"""Root conftest: set env vars before any module-level imports fire."""
import os

os.environ.setdefault("LINGO_DEV_MODE", "true")
