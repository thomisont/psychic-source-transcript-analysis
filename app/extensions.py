from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_session import Session

print("EXTENSIONS.PY: Importing extensions module now.")

# Initialize extensions
server_session = Session()
db = SQLAlchemy()
# REMOVE THE LINE BELOW as it causes a RuntimeError outside app context
# print(f"EXTENSIONS.PY: db object created: {type(db)}, has app bound: {db.app is not None or bool(getattr(db, 'engines', {})) or bool(getattr(db, '_app_engines', {}))}")
print(f"EXTENSIONS.PY: db object created (type: {type(db)}).") # Simpler print

migrate = Migrate()
cache = Cache()
