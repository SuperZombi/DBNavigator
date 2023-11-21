from flask import Flask
from db_navigator import DBNavigator


def custom_login(password):
	# make request to db
	if password == "custom_value":
		return True	


app = Flask(__name__)
DBNavigator(app, "messages.db", prefix="/admin",
	password=1234,
	#login_func=custom_login
)

@app.route("/")
def home():
	return {'online': True}

app.run(debug=True)
