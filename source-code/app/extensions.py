from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Database
db = SQLAlchemy()

# User Authentication
login_manager = LoginManager()

# Database Migrations
migrate = Migrate()
