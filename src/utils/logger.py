# src/utils/logger.py

"""
Centralized logging configuration.
"""

import logging
import os

from src.config.settings import (
    get_settings
)

settings = get_settings()

# ==========================================
# Create logs directory
# ==========================================

os.makedirs(
    os.path.dirname(settings.log_file),
    exist_ok=True
)

# ==========================================
# Log format
# ==========================================

if settings.log_format.lower() == "json":

    log_format = (
        '{"time":"%(asctime)s",'
        '"level":"%(levelname)s",'
        '"logger":"%(name)s",'
        '"message":"%(message)s"}'
    )

else:

    log_format = (
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    )

# ==========================================
# Configure logging
# ==========================================

logging.basicConfig(

    level=getattr(
        logging,
        settings.log_level.upper()
    ),

    format=log_format,

    handlers=[

        logging.FileHandler(
            settings.log_file
        ),

        logging.StreamHandler()
    ]
)

# ==========================================
# Logger factory
# ==========================================

def get_logger(name: str) -> logging.Logger:
    """
    Return configured logger.
    """

    return logging.getLogger(name)