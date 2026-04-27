from apscheduler.schedulers.background import BackgroundScheduler
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Entre com suas credenciais para acessar o painel."
login_manager.login_message_category = "warning"

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")