import datetime
import json
import logging
import logging.config


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        ms = f"{dt.microsecond // 1000:03d}"
        entry = {
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.") + ms + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging() -> None:
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": JSONFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "uvicorn":        {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.error":  {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
    })
