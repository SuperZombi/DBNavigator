import os
from flask import request, send_file, abort, redirect, make_response
import sqlite3
from jinja2 import Environment, FileSystemLoader


class DBNavigator:
	__version__ = "0.0.1"

	def __init__(self, app, file, prefix="", password=None):
		self.app = app
		self.file = os.path.abspath(file)
		self.prefix = prefix
		self.password = str(password)

		if not os.path.exists(self.file):
			raise FileNotFoundError(self.file)

		self.DB = Database(self.file)

		self.CUR_DIR = os.path.realpath(os.path.dirname(__file__))
		self.static = os.path.join(self.CUR_DIR, 'static')
		self.jinja = Environment(loader=FileSystemLoader(os.path.join(self.static, "html")))

		### Flask routes

		@app.route(f"{self.prefix}/db_navigator/<path:filename>")
		def static_file(filename):
			filepath = os.path.join(self.static, filename)
			return send_file(filepath) if os.path.exists(filepath) else abort(404)

		@app.route(f"{self.prefix}/")
		def index():
			tables = self.all_tables()
			return self.render_template("index.html", {"db_name": self.DB.name, "tables": tables})

		@app.route(f"{self.prefix}/table/<string:table_name>/")
		@app.route(f"{self.prefix}/table/<string:table_name>/<string:target>")
		def table(table_name, target=""):
			tables = self.all_tables()
			if not table_name in tables:
				return abort(404)
			data = {"db_name": self.DB.name, "table_name": table_name, "tables": tables, "current_tab": target}

			if target == "content":
				data["column_names"], data["content"] = self.table_content(table_name)
			else:
				data["structure"] = self.table_structure(table_name)

			return self.render_template("table.html", data)

		
		if password:
			@app.route(f"{self.prefix}/login", methods=['GET', 'POST'])
			def login():
				if request.method == 'POST':
					if request.form.get('password') == self.password:

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
				if request.path.startswith(self.prefix):
					if (
						request.cookies.get("db_navigator_password") != self.password and
						not request.path.startswith(f"{self.prefix}/login") and
						not request.path.startswith(f"{self.prefix}/db_navigator/")
					):
						resp = make_response(redirect(f"{self.prefix}/login"))
						resp.set_cookie("url_next", request.path)
						return resp


	def render_template(self, filename, data=None):
		template = self.jinja.get_template(filename)
		default = {"prefix": self.prefix}
		if data: data = {**default, **data}
		return template.render(data or default)

	def all_tables(self):
		tables = self.DB.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
		return [table[0] for table in tables]

	def table_structure(self, table):
		cursor = self.DB.execute(f'''PRAGMA table_info("{table}")''')
		results = cursor.fetchall()
		column_names = [column[0] for column in cursor.description]
		data = [dict(zip(column_names, row)) for row in results]
		return data

	def table_content(self, table):
		cursor = self.DB.execute(f'''SELECT * FROM "{table}"''')
		column_names = [column[0] for column in cursor.description]
		results = cursor.fetchall()
		return column_names, results


class Database:
	def __init__(self, file):
		self.file = file
		self.name = os.path.basename(file)
		self.conn = sqlite3.connect(file, check_same_thread=False)

	def execute(self, command, args=None):
		cursor = self.conn.cursor()
		cursor.execute(command, args or ())
		return cursor

	def save(self):
		self.conn.commit()
