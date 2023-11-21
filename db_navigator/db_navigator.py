import os
from flask import request, jsonify, send_file, abort, redirect, make_response
import sqlite3
from jinja2 import Environment, FileSystemLoader


class DBNavigator:
	__version__ = "0.0.1"

	def __init__(self, app, file, prefix="", password="", login_func=None, readonly=False):
		self.app = app
		self.file = os.path.abspath(file)
		self.prefix = prefix
		self.password = str(password)
		self.readonly = readonly
		self.login_func = login_func

		if not os.path.exists(self.file):
			raise FileNotFoundError(self.file)

		self.DB = Database(self.file, readonly)

		self.CUR_DIR = os.path.realpath(os.path.dirname(__file__))
		self.static = os.path.join(self.CUR_DIR, 'static')
		self.jinja = Environment(loader=FileSystemLoader(os.path.join(self.static, "html")))

		### Flask routes

		@app.route(f"{self.prefix}/files/<path:filename>")
		def static_file(filename):
			filepath = os.path.join(self.static, filename)
			return send_file(filepath) if os.path.exists(filepath) else abort(404)

		@app.route(f"{self.prefix}/")
		def index():
			tables = self.all_tables()
			return self.render_template("index.html", {"db_name": self.DB.name, "tables": tables})

		@app.route(f"{self.prefix}/table/<string:table_name>/")
		@app.route(f"{self.prefix}/table/<string:table_name>/<string:target>", methods=['GET', 'POST'])
		def table(table_name, target=""):
			tables = self.all_tables()
			if not table_name in tables:
				return abort(404)
			data = {"db_name": self.DB.name, "table_name": table_name, "tables": tables, "current_tab": target}

			if target in ["insert", "edit", "delete", "delete_table_data", "drop_table"] and self.readonly:
				return abort(405)

			if target == "content":
				sorting = request.args.get('sort')
				if sorting:
					data["sort_type"] = "desc" if sorting.startswith("-") else "asc"
					data["sorting"] = sorting.lstrip("-")
				data["column_names"], data["content"] = self.table_content(table_name, sort_by=sorting)
				data["rows_count"] = self.table_rows_count(table_name)

			elif target == "delete" and not self.readonly:
				rows = request.args.get("rows")
				self.delete_rows(table_name, rows)
				new_url = request.args.get("redirect", f"{self.prefix}/table/{table_name}/")
				return redirect(new_url)

			elif target == "insert" and request.method == 'POST':
				result = self.insert_row(table_name, dict(request.form))
				result_data = {}
				if result != True:
					result_data["sql_error"] = str(result)
				return jsonify({"successfully": result == True, **result_data})

			elif target == "edit":
				rowid = request.args.get("row")
				if request.method == 'POST':
					result = self.update_row(table_name, rowid, dict(request.form))
					result_data = {}
					if result != True:
						result_data["sql_error"] = str(result)
					return jsonify({"successfully": result == True, **result_data})
				else:
					row_data = self.row_content(table_name, rowid)
					if not row_data:
						return abort(404)
					data["structure"] = [{**item, 'value': row_data.get(item['name']) or ''} for item in self.table_structure(table_name)[0]]
			
			elif target == "delete_table_data":
				self.delete_table_data(table_name)
				return redirect(f"{self.prefix}/table/{table_name}/")
			
			elif target == "drop_table":
				self.drop_table(table_name)
				return redirect(f"{self.prefix}/")

			else:
				data["structure"], data["foreign_keys"] = self.table_structure(table_name)

			return self.render_template("table_base.html", data)


		@app.route(f"{self.prefix}/sql", methods=['GET', 'POST'])
		def sql():
			if request.method == 'POST':
				if request.json.get('query') != "":
					result = self.execute_sql(request.json['query'])	
				return jsonify(result)
			return self.render_template("sql.html", {"db_name": self.DB.name})

		
		if password or login_func:
			@app.route(f"{self.prefix}/login", methods=['GET', 'POST'])
			def login():
				if request.method == 'POST':
					if login_func:
						result = login_func(request.form.get('password'))
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

			@app.route(f"{self.prefix}/logout")
			def logout():
				resp = make_response(redirect(f"{self.prefix}/login"))
				resp.set_cookie("db_navigator_password", '', expires=0)
				return resp

			@app.before_request
			def check_password():
				if (request.path.startswith(self.prefix) and
					not request.path.startswith(f"{self.prefix}/login") and
					not request.path.startswith(f"{self.prefix}/files/") # resources
				):
					if login_func:
						result = login_func(request.cookies.get("db_navigator_password"))
					else:
						result = request.cookies.get("db_navigator_password") == self.password

					if not result:
						resp = make_response(redirect(f"{self.prefix}/login"))
						resp.set_cookie("url_next", request.path)
						return resp


	def render_template(self, filename, data=None):
		template = self.jinja.get_template(filename)
		default = {
			"prefix": self.prefix,
			"show_logout": self.password != "" or self.login_func != None,
			"readonly": self.readonly
		}
		if data: data = {**default, **data}
		return template.render(data or default)

	def all_tables(self):
		tables = self.DB.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
		return [table[0] for table in tables]

	def table_structure(self, table):
		'''
		Returns columns data and foreign keys: [data, foreign_keys]
		'''
		cursor = self.DB.execute(f'''PRAGMA table_info("{table}")''')
		results = cursor.fetchall()
		column_names = [column[0] for column in cursor.description]
		data = [dict(zip(column_names, row)) for row in results]

		cursor = self.DB.execute(f'''PRAGMA foreign_key_list("{table}")''')
		results = cursor.fetchall()
		column_names = [column[0] for column in cursor.description]
		foreign_keys = [dict(zip(column_names, row)) for row in results]

		return data, foreign_keys

	def table_rows_count(self, table):
		return self.DB.execute(f'''SELECT COUNT(*) FROM "{table}"''').fetchone()[0]

	def table_content(self, table, sort_by=None):
		'''
		Returns columns names and values: [ [column_names], [{row_id, data}, ...] ]
		'''
		command = f'''SELECT rowid AS rowid, * FROM "{table}"'''

		if sort_by:
			command += f''' ORDER BY "{sort_by.lstrip("-")}"'''
			if sort_by.startswith("-"):
				command += " DESC"
		
		cursor = self.DB.execute(command)
		column_names = [column[0] for column in cursor.description]
		results = cursor.fetchall()
		data = map(lambda row: {"rowid": row[0], "data": row[1:]}, results)
		return column_names[1:], data

	def row_content(self, table, rowid):
		cursor = self.DB.execute(f'''SELECT * FROM "{table}" WHERE ROWID = {rowid}''')
		result = cursor.fetchone()
		if not result: return {}
		column_names = [column[0] for column in cursor.description]
		data = dict(zip(column_names, result))
		return data

	def delete_rows(self, table, rows):
		if self.readonly: raise PermissionError("Database is read-only!")
		self.DB.execute(f'''DELETE FROM "{table}" WHERE ROWID IN ({rows})''')
		self.DB.save()

	def insert_row(self, table, data):
		if self.readonly: raise PermissionError("Database is read-only!")
		try:
			command = f'''INSERT INTO "{table}" ({",".join(data.keys())})
				VALUES ({",".join(["?" for _ in range(len(data.values()))])})'''
			self.DB.execute(command, [None if x == "" else x for x in data.values()])
			self.DB.save()
			return True
		except Exception as e:
			return e

	def update_row(self, table, rowid, data):
		if self.readonly: raise PermissionError("Database is read-only!")
		try:
			command = f'''UPDATE "{table}" SET {",".join([f'"{key}" = ?' for key in data.keys()])}
				WHERE ROWID = {rowid}'''
			self.DB.execute(command, [None if x == "" else x for x in data.values()])
			self.DB.save()
			return True
		except Exception as e:
			return e

	def delete_table_data(self, table):
		if self.readonly: raise PermissionError("Database is read-only!")
		self.DB.execute(f'''DELETE FROM "{table}"''')
		self.DB.save()

	def drop_table(self, table):
		if self.readonly: raise PermissionError("Database is read-only!")
		# PRAGMA foreign_keys=on/off
		self.DB.execute(f'''DROP TABLE "{table}"''')
		self.DB.save()

	def execute_sql(self, query):
		answer = {"successfully": True}
		try:
			cursor = self.DB.execute(query)
			results = cursor.fetchall()
			if len(results) > 0:
				column_names = [column[0] for column in cursor.description]
				answer["column_names"] = column_names
				answer["data"] = results
				answer["rowcount"] = len(results)
			else:
				if self.readonly:
					answer["total_changes"] = 0
					cursor.connection.rollback()
				else:
					answer["total_changes"] = cursor.connection.total_changes
					self.DB.save()
		except Exception as e:
			answer["successfully"] = False
			answer["error"] = str(e)
		
		return answer


class Database:
	def __init__(self, file, readonly=False):
		self.file = file
		self.name = os.path.basename(file)
		if readonly:
			self.conn = sqlite3.connect(f'file:{file}?mode=ro', uri=True, check_same_thread=False)
		else:
			self.conn = sqlite3.connect(file, check_same_thread=False)

	def execute(self, command, args=None):
		cursor = self.conn.cursor()
		cursor.execute(command, args or ())
		return cursor

	def save(self):
		self.conn.commit()
