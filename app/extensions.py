from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Instantiate extensions globally
db = SQLAlchemy()
migrate = Migrate() 