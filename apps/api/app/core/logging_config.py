# file: apps/api/app/core/logging_config.py
"""Application log formats with conservative credential and exception handling."""
import json
import logging
import re
import sys
from logging.config import dictConfig


class JsonFormatter(logging.Formatter):
    def __init__(self, *args, secret_values=(), text=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_values = tuple(sorted({str(v) for v in secret_values if v}, key=len, reverse=True))
        self.text = text

    def redact(self, value):
        text = str(value)
        for secret in self.secret_values:
            text = text.replace(secret, '[REDACTED]')
        text = re.sub(r'(?i)\bBearer\s+[^\s,;]+', 'Bearer [REDACTED]', text)
        text = re.sub(r'(?i)(\b(?:api[_-]?key|password|passwd|token|secret|authorization|cookie)\b[\"\x27]?\s*[:=]\s*)(?:\"[^\"]*\"|\x27[^\x27]*\x27|[^\s,;]+)', r'\1[REDACTED]', text)
        text = re.sub(r'(://)[^\s/@:]+:[^\s/@]+@', r'\1[REDACTED]@', text)
        return text

    def format(self, record):
        # Never serialize arbitrary extras, provider payloads, or exception text.
        row = {'timestamp': self.formatTime(record, self.datefmt), 'level': record.levelname,
               'message': self.redact(record.getMessage()), 'name': record.name}
        if record.exc_info:
            row['exc_info'] = {'type': record.exc_info[0].__name__ if record.exc_info[0] else 'unknown'}
        for field in ('correlation_id', 'request_id'):
            value = getattr(record, field, None)
            if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
                row[field] = self.redact(value)
        if self.text:
            return f"{row['timestamp']} {row['level']} {row['name']} {row['message']}" + (
                f" exception_type={row['exc_info']['type']}" if 'exc_info' in row else '')
        return json.dumps(row, ensure_ascii=False)


def setup_logging(*, log_format='json', level='INFO', secret_values=()):
    if log_format not in {'json', 'text'}:
        raise ValueError('Unsupported application log format')
    config = {'version': 1, 'disable_existing_loggers': False,
              'formatters': {'json': {'()': JsonFormatter, 'secret_values': secret_values,
                                      'text': log_format == 'text'}},
              'handlers': {'stdout': {'class': 'logging.StreamHandler', 'stream': sys.stdout,
                                      'formatter': 'json'}},
              'root': {'level': level.upper(), 'handlers': ['stdout']}}
    dictConfig(config)
