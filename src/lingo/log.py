"""Logging configuration for Lingo."""

import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(level: str) -> None:
    """Configure root logger to emit levelled output in uvicorn's visual style."""
    logging.basicConfig(
        level=level.upper(),
        format="%(levelname)-8s %(name)s: %(message)s",
    )
