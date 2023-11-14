from flask import Flask
from db_navigator import *

app = Flask(__name__)
DBNavigator(app, "users.db", prefix="/admin", password=1234)

@app.route("/")
def home():
	return {'online': True}

app.run(debug=True)
