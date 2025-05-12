from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_session import Session

# Initialize extensions
server_session = Session()
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
