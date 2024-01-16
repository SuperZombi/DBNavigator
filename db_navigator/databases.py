import os
import sqlite3
from typing import List, Dict, Any, TypedDict
from abc import ABC, abstractmethod


class RowStructure(TypedDict):
	name: str
	type: str
	pk: bool # primary key
	notnull: bool
	dflt_value: Any

class ForeignKey(TypedDict):
	from_column: str
	to_table: str
	to_column: str

class TableContentModel(TypedDict):
	row_id: int
	data: List[Any]

class QueryResult(TypedDict):
	successfully: bool
	error: str
	total_changes: int
	rowcount: int
	column_names: List[str]
	data: Dict[str, Any]


class DataBaseInterface(ABC):
	def __init__(self, file:str, readonly:bool=False):
		self.file = file
		self.__name__ = None # Interface name
		self.name = os.path.basename(file) # DB name
		self.readonly = readonly

	@abstractmethod
	def all_tables(self) -> List[str]: pass

	@abstractmethod
	def table_structure(self, table_name:str) -> List[RowStructure]: pass

	@abstractmethod
	def table_foreign_keys(self, table_name:str) -> List[ForeignKey]: pass

	@abstractmethod
	def table_columns_names(self, table_name:str) -> List[str]: pass

	@abstractmethod
	def table_rows_count(self, table_name:str) -> int: pass

	@abstractmethod
	def table_content(self, table_name:str, sort_by:str=None) -> List[TableContentModel]: pass

	@abstractmethod
	def row_content(self, table_name:str, rowid:int) -> Dict[str, Any]: pass

	@abstractmethod
	def delete_rows(self, table_name:str, rows:List[int]): pass

	@abstractmethod
	def insert_row(self, table_name:str, data:Dict[str, Any]): pass

	@abstractmethod
	def update_row(self, table_name:str, rowid:int, new_data:Dict[str, Any]): pass

	@abstractmethod
	def delete_table_data(self, table_name:str): pass

	@abstractmethod
	def drop_table(self, table_name:str): pass

	@abstractmethod
	def execute_sql(self, query:str) -> QueryResult: pass



class SQLite(DataBaseInterface):
	def __init__(self, *args):
		super().__init__(*args)
		self.__name__ = "SQLite3"

	def execute(self, command, args=None, after=None, save=False):
		with sqlite3.connect(self.file, check_same_thread=False) as conn:
			cursor = conn.cursor()
			cursor.execute("begin")
			cursor.execute(command, args or ())
			if after: return after(cursor)
			if save: conn.commit()
			else: conn.rollback()


	def all_tables(self):
		def after(cursor): return [table[0] for table in cursor.fetchall()]
		return self.execute("SELECT name FROM sqlite_master WHERE type='table'", after=after)

	def table_structure(self, table):
		def after(cursor):
			column_names = [column[0] for column in cursor.description]
			return [dict(zip(column_names, row)) for row in cursor.fetchall()]
		return self.execute(f'''PRAGMA table_info("{table}")''', after=after)

	def table_foreign_keys(self, table):
		def after(cursor):
			column_names = [column[0] for column in cursor.description]
			arr = [dict(zip(column_names, row)) for row in cursor.fetchall()]
			return list(map(lambda e: {'from_column': e['from'], 'to_table': e['table'], 'to_column': e['to']}, arr))
		return self.execute(f'''PRAGMA foreign_key_list("{table}")''', after=after)

	def table_columns_names(self, table):
		def after(cursor): return [column[0] for column in cursor.fetchall()]
		return self.execute(f'''SELECT name FROM PRAGMA_TABLE_INFO("{table}")''', after=after)

	def table_rows_count(self, table):
		return self.execute(f'''SELECT COUNT(*) FROM "{table}"''', after=lambda cur: cur.fetchone()[0])

	def table_content(self, table, sort_by=None):
		def after(cursor):
			return map(lambda row: {"rowid": row[0], "data": row[1:]}, cursor.fetchall())
		command = f'''SELECT rowid AS rowid, * FROM "{table}"'''
		if sort_by:
			command += f''' ORDER BY "{sort_by.lstrip("-")}"'''
			if sort_by.startswith("-"):
				command += " DESC"
		return self.execute(command, after=after)

	def row_content(self, table, rowid):
		def after(cursor):
			result = cursor.fetchone()
			if not result: return {}
			column_names = [column[0] for column in cursor.description]
			return dict(zip(column_names, result))
		return self.execute(f'''SELECT * FROM "{table}" WHERE ROWID = {rowid}''', after=after)

	def delete_rows(self, table, rows):
		if self.readonly: raise PermissionError("Database is read-only!")
		self.execute(f'''DELETE FROM "{table}" WHERE ROWID IN ({rows})''', save=True)

	def insert_row(self, table, data):
		if self.readonly: raise PermissionError("Database is read-only!")
		try:
			command = f'''INSERT INTO "{table}" ({",".join(data.keys())})
				VALUES ({",".join(["?" for _ in range(len(data.values()))])})'''
			self.execute(command, [None if x == "" else x for x in data.values()], save=True)
			return True
		except Exception as e:
			return e

	def update_row(self, table, rowid, data):
		if self.readonly: raise PermissionError("Database is read-only!")
		try:
			command = f'''UPDATE "{table}" SET {",".join([f'"{key}" = ?' for key in data.keys()])}
				WHERE ROWID = {rowid}'''
			self.execute(command, [None if x == "" else x for x in data.values()], save=True)
			return True
		except Exception as e:
			return e

	def delete_table_data(self, table):
		if self.readonly: raise PermissionError("Database is read-only!")
		self.execute(f'''DELETE FROM "{table}"''', save=True)

	def drop_table(self, table):
		if self.readonly: raise PermissionError("Database is read-only!")
		# PRAGMA foreign_keys=on/off
		self.execute(f'''DROP TABLE "{table}"''', save=True)

	def execute_sql(self, query):
		def after(cursor):
			answer = {"successfully": True}
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
					cursor.connection.commit()
			return answer
		try:
			return self.execute(query, after=after)
		except Exception as e:
			return {"successfully": False, "error": str(e)}
