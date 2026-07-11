from flask import Flask
from config import Config
from app.extensions import db, login_manager, migrate
from app.models import Department, Employee, User




def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)



    login_manager.login_view = "auth.login"

    @app.route("/")
    def home():
        return """
        <h1>BUYOH Payroll System</h1>
        <h3>Flask Extensions Loaded Successfully</h3>
        """

    return app
