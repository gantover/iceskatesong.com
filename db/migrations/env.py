# Plain-SQL migrations: no models, no autogenerate, online mode only.
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

# DATABASE_URL is a plain postgres:// URL shared with web; SQLAlchemy needs the driver named.
url = "postgresql+psycopg://" + os.environ["DATABASE_URL"].split("://", 1)[1]

with create_engine(url).connect() as connection:
    context.configure(connection=connection, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()
