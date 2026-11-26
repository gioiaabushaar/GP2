
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.core.db import Base
from app.core import models  # noqa: F401
# Tables that live in their own modules instead of app/core/models.py:
from app.modules.web_labs import models as web_lab_models  # noqa: F401
from app.modules.deployments import models as deployment_models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the database URL configured by NEXIS.
config.set_main_option(
    "sqlalchemy.url",
    settings.nexis_database_url.replace("%", "%%")
)

# Load all SQLAlchemy table definitions.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.nexis_database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()



def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
            autogenerate_plugins=[
                "alembic.autogenerate.*",
                "alembic.ext.checkconstraint_byname",
            ],
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
