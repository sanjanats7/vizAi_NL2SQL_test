import logging
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler

class LoggingConfig:
    """
    Configures logging for the FastAPI application with log rotation.
    """
    LOG_FILE = "app.log"
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "[%(asctime)s] %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FILE,
                "formatter": "detailed",
                "level": "INFO",
                "maxBytes": 5 * 1024 * 1024,  # 5MB file size limit
                "backupCount": 3,  # Keep 3 old logs
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "app": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
            "api": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "db": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            }
        }
    }

    @staticmethod
    def apply():
        dictConfig(LoggingConfig.LOGGING_CONFIG)
