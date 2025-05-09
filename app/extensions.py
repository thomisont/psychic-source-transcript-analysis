import logging
import sqlalchemy
logging.warning(f"SQLAlchemy imported from: {sqlalchemy.__file__}")
logging.warning(f"SQLAlchemy version: {sqlalchemy.__version__}")

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Instantiate extensions globally
db = SQLAlchemy()
migrate = Migrate() 