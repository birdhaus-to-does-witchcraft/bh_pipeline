"""
Logging configuration and setup for the Wix API data pipeline.

This module provides consistent logging across the entire pipeline with both
file and console output, structured formatting, and configurable log levels.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    log_name: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging with file and console handlers.

    Args:
        log_dir: Directory to store log files (default: "logs")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_name: Optional name for the logger (defaults to root logger)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging(log_dir="logs", log_level="INFO")
        >>> logger.info("Starting data extraction...")
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Generate timestamped log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"pipeline_{timestamp}.log"

    # Get or create logger
    logger = logging.getLogger(log_name) if log_name else logging.getLogger()

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        fmt='%(levelname)s: %(message)s'
    )

    # File handler (detailed logging)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler (simplified output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing events...")
    """
    return logging.getLogger(name)


class PipelineLogger:
    """
    Context manager for pipeline-specific logging with progress tracking.

    Example:
        >>> with PipelineLogger("events") as logger:
        ...     logger.start("Extracting events from Wix API")
        ...     # Do work...
        ...     logger.success(f"Extracted {count} events")
    """

    def __init__(self, entity_type: str, log_dir: str = "logs"):
        """
        Initialize pipeline logger for a specific entity type.

        Args:
            entity_type: Type of entity being processed (e.g., "events", "guests")
            log_dir: Directory to store log files
        """
        self.entity_type = entity_type
        self.log_dir = log_dir
        self.logger = None
        self.start_time = None

    def __enter__(self):
        """Set up logging when entering context."""
        self.logger = setup_logging(
            log_dir=self.log_dir,
            log_name=f"pipeline.{self.entity_type}"
        )
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up and log final status when exiting context."""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(
                f"Pipeline completed successfully for {self.entity_type} "
                f"(duration: {duration:.2f}s)"
            )
        else:
            self.logger.error(
                f"Pipeline failed for {self.entity_type} "
                f"(duration: {duration:.2f}s): {exc_val}",
                exc_info=True
            )

        return False  # Don't suppress exceptions

    def start(self, message: str):
        """Log the start of a pipeline stage."""
        self.logger.info(f"Starting: {message}")

    def progress(self, message: str):
        """Log progress update."""
        self.logger.info(message)

    def success(self, message: str):
        """Log successful completion of a stage."""
        self.logger.info(f"✓ {message}")

    def warning(self, message: str):
        """Log a warning."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log an error."""
        self.logger.error(message, exc_info=exc_info)
