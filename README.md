<h1 align="center">DB Navigator</h1>
<p align="center">
    <img src="https://raw.githubusercontent.com/SuperZombi/DBNavigator/main/github/images/logo.png" width="200">
</p>
<h3 align="center">DataBase Navigator for Flask</h3>
<p align="center">
    <img src="https://shields.io/badge/version-v0.1.1-blue">
</p>

<img width="500px" src="https://raw.githubusercontent.com/SuperZombi/DBNavigator/main/github/images/preview.png">

<details>
<summary>More images</summary>
<img width="500px" src="https://raw.githubusercontent.com/SuperZombi/DBNavigator/main/github/images/preview_dark.png"></br>
<img width="500px" src="https://raw.githubusercontent.com/SuperZombi/DBNavigator/main/github/images/preview_edit.png"></br>
<img width="500px" src="https://raw.githubusercontent.com/SuperZombi/DBNavigator/main/github/images/preview_sql.png">
</details>


## Installation
```
pip install DBNavigator
```

## Usage:
```python
from flask import Flask
from db_navigator import DBNavigator

app = Flask(__name__)
DBNavigator(app, "users.db", prefix="/admin", password="1234")

### Your Flask app

app.run(debug=True)
```

### DBNavigator(`app`, `file`, `prefix=""`, `password=""`, `login_func=None`, `readonly=False`)
| <!-- --> | <!-- --> |
|----------|----------|
| `app`    | Flask app |
| `file`   | Target database local file|
| `prefix`   | Route prefix |
| `password`   | Access password |
| `login_func`   | [Custom login function](#custom-login) |
| `readonly`   | Default editable |

<hr>

### Custom login
Must be returned `True` for access.<br>
It is recommended to save the password from the database in memory because it will be checked before each request.
```python
def custom_login(password):
	# make request to db
	if password == "custom_value":
		return True	

DBNavigator(app, "users.db", login_func=custom_login)
```
