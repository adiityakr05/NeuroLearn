import pytest
import os
from alembic.config import Config
from alembic import command
from app.core.config import settings


def test_alembic_migration_execution():
    """
    Verifies that Alembic migrations run cleanly against the database
    and can upgrade to head without error.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")
