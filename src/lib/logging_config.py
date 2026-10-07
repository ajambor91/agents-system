"""Shared Python logging setup; RFC 5424 records go to stderr/journald."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import socket
import sys
from threading import RLock

_LOCK = RLock()


def _header(value: object, limit: int) -> str:
    """RFC 5424 header fields accept printable US-ASCII without spaces."""
    return ''.join(char if 33 <= ord(char) <= 126 else '_' for char in str(value))[:limit] or '-'


class RFC5424Formatter(logging.Formatter):
    def __init__(self, application: str) -> None:
        super().__init__()
        self.application = _header(application, 48)
        self.hostname = _header(socket.gethostname(), 255)

    def format(self, record: logging.LogRecord) -> str:
        severity = (2 if record.levelno >= logging.CRITICAL else
                    3 if record.levelno >= logging.ERROR else
                    4 if record.levelno >= logging.WARNING else
                    6 if record.levelno >= logging.INFO else 7)
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        message = record.getMessage()
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        if record.stack_info:
            message += '\n' + self.formatStack(record.stack_info)
        # One physical record per line, including tracebacks and untrusted values.
        message = message.replace('\\', '\\\\').replace('\r', '\\r').replace('\n', '\\n').replace('\x00', '\\0')
        # Facility daemon (3), NILVALUE structured data, UTF-8 BOM for MSG.
        return (f'<{24 + severity}>1 {timestamp} {self.hostname} {self.application} '
                f'{record.process} {_header(record.name.rsplit('.', 1)[-1], 32)} - \ufeff{message}')


class _StderrHandler(logging.StreamHandler):
    """Keep the startup stderr stream outside runtime output capture."""


def configure_logging(application: str) -> None:
    """Configure once per process; systemd AGENTS_MANAGER_LOG_LEVEL wins, default is INFO."""
    with _LOCK:
        root = logging.getLogger()
        existing = next((h for h in root.handlers if isinstance(h, _StderrHandler)), None)
        if existing is not None:
            return
        requested = os.environ.get('AGENTS_MANAGER_LOG_LEVEL', 'INFO').strip().upper()
        levels = {name: value for name, value in (
            ('DEBUG', logging.DEBUG), ('INFO', logging.INFO),
            ('WARNING', logging.WARNING), ('ERROR', logging.ERROR),
            ('CRITICAL', logging.CRITICAL),
        )}
        root.setLevel(levels.get(requested, logging.INFO))
        handler = _StderrHandler()
        handler.setFormatter(RFC5424Formatter(application))
        root.addHandler(handler)
        if requested not in levels:
            logging.getLogger(__name__).warning('Invalid AGENTS_MANAGER_LOG_LEVEL=%r; using INFO', requested)
