import os
from flask import request, jsonify, send_file, abort, redirect, make_response
from jinja2 import Environment, FileSystemLoader
from .databases import SQLite


class DBNavigator:
	__version__ = "0.2.1"

	def __init__(self, app, file, prefix="", password="", login_func=None, readonly=False, db_engine=None):
		self.app = app
		self.file = os.path.abspath(file)
		self.prefix = prefix
		self.password = str(password)
		self.readonly = readonly
		self.login_func = login_func

		if not os.path.exists(self.file): raise FileNotFoundError(self.file)
		db_engine = db_engine or SQLite
		self.DB = db_engine(self.file, self.readonly)

		self.CUR_DIR = os.path.realpath(os.path.dirname(__file__))
		self.static = os.path.join(self.CUR_DIR, 'static')
		self.jinja = Environment(loader=FileSystemLoader(os.path.join(self.static, "html")))
		self.init_routes()

	def init_routes(self):
		@self.app.route(f"{self.prefix}/files/<path:filename>")
		def static_file(filename):
			filepath = os.path.join(self.static, filename)
			return send_file(filepath) if os.path.exists(filepath) else abort(404)

		@self.app.route(f"{self.prefix}/")
		def index():
			tables = self.DB.all_tables()
			return self.render_template("index.html", {"tables": tables})

		@self.app.route(f"{self.prefix}/table/<string:table_name>/")
		@self.app.route(f"{self.prefix}/table/<string:table_name>/<string:target>", methods=['GET', 'POST'])
		def table(table_name, target=""):
			tables = self.DB.all_tables()
			if not table_name in tables:
				return abort(404)
			data = {"table_name": table_name, "tables": tables, "current_tab": target}

			if target in ["insert", "edit", "delete", "delete_table_data", "drop_table"] and self.readonly:
				return abort(405)

			if target == "content":
				sorting = request.args.get('sort')
				if sorting:
					data["sort_type"] = "desc" if sorting.startswith("-") else "asc"
					data["sorting"] = sorting.lstrip("-")

				data["column_names"] = self.DB.table_columns_names(table_name)
				data["rows_count"] = self.DB.table_rows_count(table_name)
				data["content"] = self.DB.table_content(table_name, sort_by=sorting)

			elif target == "delete" and not self.readonly:
				rows = request.args.get("rows")
				self.DB.delete_rows(table_name, rows)
				new_url = request.args.get("redirect", f"{self.prefix}/table/{table_name}/")
				return redirect(new_url)

			elif target == "insert" and request.method == 'POST':
				result = self.DB.insert_row(table_name, dict(request.form))
				result_data = {}
				if result != True:
					result_data["sql_error"] = str(result)
				return jsonify({"successfully": result == True, **result_data})

			elif target == "edit":
				rowid = request.args.get("row")
				if request.method == 'POST':
					result = self.DB.update_row(table_name, rowid, dict(request.form))
					result_data = {}
					if result != True:
						result_data["sql_error"] = str(result)
					return jsonify({"successfully": result == True, **result_data})
				else:
					row_data = self.DB.row_content(table_name, rowid)
					if not row_data: return abort(404)
					data["structure"] = [{**item, 'value': row_data.get(item['name']) or ''} for item in self.DB.table_structure(table_name)]
			
			elif target == "delete_table_data":
				self.DB.delete_table_data(table_name)
				return redirect(f"{self.prefix}/table/{table_name}/")
			
			elif target == "drop_table":
				self.DB.drop_table(table_name)
				return redirect(f"{self.prefix}/")

			else:
				data["structure"] = self.DB.table_structure(table_name)
				data["foreign_keys"] = self.DB.table_foreign_keys(table_name)

			return self.render_template("table_base.html", data)


		@self.app.route(f"{self.prefix}/sql", methods=['GET', 'POST'])
		def sql():
			if request.method == 'POST':
				if request.json.get('query') != "":
					result = self.DB.execute_sql(request.json['query'])
				return jsonify(result)
			return self.render_template("sql.html")

		
		if self.password or self.login_func:
			@self.app.route(f"{self.prefix}/login", methods=['GET', 'POST'])
			def login():
				if request.method == 'POST':
					if self.login_func:
						result = self.login_func(request.form.get('password'))
					else:
						result = request.form.get('password') == self.password

					if result:
						if request.cookies.get("url_next"):
							resp = make_response(redirect(request.cookies.get("url_next")))
						else:
							resp = make_response(redirect(f"{self.prefix}/"))

						resp.set_cookie("url_next", '', expires=0)
						resp.set_cookie('db_navigator_password', request.form.get('password'))
						return resp
					return self.render_template("login.html", {"message": "Invalid password!"})
				return self.render_template("login.html")

			@self.app.route(f"{self.prefix}/logout")
			def logout():
				resp = make_response(redirect(f"{self.prefix}/login"))
				resp.set_cookie("db_navigator_password", '', expires=0)
				return resp

			@self.app.before_request
			def check_password():
				if (request.path.startswith(self.prefix) and
					not request.path.startswith(f"{self.prefix}/login") and
					not request.path.startswith(f"{self.prefix}/files/")
				):
					if self.login_func:
						result = self.login_func(request.cookies.get("db_navigator_password"))
					else:
						result = request.cookies.get("db_navigator_password") == self.password

					if not result:
						resp = make_response(redirect(f"{self.prefix}/login"))
						resp.set_cookie("url_next", request.path)
						return resp


	def render_template(self, filename, data=None):
		template = self.jinja.get_template(filename)
		default = {
			"db_name": self.DB.name,
			"prefix": self.prefix,
			"show_logout": self.password != "" or self.login_func != None,
			"version": self.__version__,
			"readonly": self.readonly
		}
		if data: data = {**default, **data}
		return template.render(data or default)
