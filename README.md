# DB Navigator
### DataBase Navigator for Flask
<img src="https://shields.io/badge/version-v0.0.1-blue">

<img width="60%" src="github/images/preview.png">

### Usage:
```python
from flask import Flask
from db_navigator import DBNavigator

app = Flask(__name__)
DBNavigator(app, "users.db", prefix="/admin", password="1234")

app.run(debug=True)
```
