"""Root conftest: set env vars before any module-level imports fire."""

import os

os.environ["LINGO_DEV_MODE"] = "true"
os.environ["LINGO_SLACK_BOT_TOKEN"] = "xoxb-dummy"
os.environ["LINGO_SLACK_SIGNING_SECRET"] = "dummy-secret"
