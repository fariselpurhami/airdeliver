# This file correctly triggers the loading of all models
# via the app/models/__init__.py file.

from app.db.base_class import Base  # noqa
from app import models  # noqa
