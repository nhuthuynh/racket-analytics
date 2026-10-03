"""Alembic environment (ST-005). Runs online only, on the connection ``upgrade_to_head`` passes."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from racket.platform.db import sqlalchemy_url

connection = context.config.attributes.get("connection")
if connection is None:  # `alembic -x url=...` from a shell
    url = context.get_x_argument(as_dictionary=True)["url"]
    with create_engine(sqlalchemy_url(url)).connect() as conn:
        context.configure(connection=conn)
        with context.begin_transaction():
            context.run_migrations()
else:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
