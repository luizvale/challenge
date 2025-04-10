"""
Enhanced logging facilities for the resource manager.

This module provides an enhanced logger that supports structured logging,
colorized output, and integration with the resource manager.
"""
import logging
import os
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime


class ResourceManagerLogger:
    """
    Enhanced logger for the resource manager.
    
    This class wraps a standard Python logger and adds features like
    structured logging, colorized output, and context tracking.
    """
    
    # ANSI color codes for colorized output
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }
    
    # Log level colors
    LEVEL_COLORS = {
        logging.DEBUG: COLORS['cyan'],
        logging.INFO: COLORS['green'],
        logging.WARNING: COLORS['yellow'],
        logging.ERROR: COLORS['red'],
        logging.CRITICAL: COLORS['bright_red'] + COLORS['bold'],
    }
    
    def __init__(
        self,
        name: str = "resource_manager",
        level: int = logging.INFO,
        use_colors: Optional[bool] = None,
        structured_output: bool = False,
        log_file: Optional[str] = None,
    ):
        """
        Initialize the resource manager logger.
        
        Args:
            name: Name of the logger
            level: Initial logging level
            use_colors: Whether to use colored output (auto-detected if None)
            structured_output: Whether to output logs in JSON format
            log_file: Optional file to write logs to
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Detect color support if not specified
        if use_colors is None:
            use_colors = sys.stdout.isatty() and os.name != 'nt'
        
        self.use_colors = use_colors
        self.structured_output = structured_output
        
        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_formatter = self._create_formatter(use_colors=use_colors, structured=structured_output)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = self._create_formatter(use_colors=False, structured=structured_output)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Context tracking
        self.context: Dict[str, Any] = {}

    def _create_formatter(self, use_colors: bool = False, structured: bool = False) -> logging.Formatter:
        """
        Create a log formatter based on configuration.

        Args:
            use_colors: Whether to use colored output
            structured: Whether to output logs in JSON format

        Returns:
            logging.Formatter: Configured formatter
        """
        if structured:
            return logging.Formatter('%(message)s')

        # Use a simple format string that doesn't depend on color variables
        format_str = '%(asctime)s | %(levelname)-8s | %(name)s - %(message)s'

        return logging.Formatter(format_str)

    def _format_message(self, level: int, msg: str, **kwargs) -> str:
        """
        Format a log message based on configuration.

        Args:
            level: Log level
            msg: Message to format
            **kwargs: Additional context for structured logging

        Returns:
            str: Formatted message
        """
        if self.structured_output:
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'level': logging.getLevelName(level),
                'message': msg,
                **self.context
            }

            if kwargs:
                log_data['data'] = kwargs

            return json.dumps(log_data)

        # Apply colors directly to the message, not relying on formatter
        if self.use_colors:
            color = self.LEVEL_COLORS.get(level, self.COLORS['reset'])
            # Return message with colors already applied
            return f"{color}{msg}{self.COLORS['reset']}"

        # Without colors
        return msg
    
    def set_level(self, level: int) -> None:
        """
        Set the logging level.
        
        Args:
            level: New logging level
        """
        self.logger.setLevel(level)
    
    def set_context(self, **kwargs) -> None:
        """
        Set context data to include in all log messages.
        
        Args:
            **kwargs: Context data as key-value pairs
        """
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context data."""
        self.context.clear()
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(self._format_message(logging.DEBUG, msg, **kwargs))
    
    def info(self, msg: str, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(self._format_message(logging.INFO, msg, **kwargs))
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(self._format_message(logging.WARNING, msg, **kwargs))
    
    def error(self, msg: str, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(self._format_message(logging.ERROR, msg, **kwargs))
    
    def critical(self, msg: str, **kwargs) -> None:
        """Log a critical message."""
        self.logger.critical(self._format_message(logging.CRITICAL, msg, **kwargs))
    
    def log_resource_event(
        self,
        resource_name: str,
        event_type: str,
        duration: Optional[float] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a resource-related event with standardized format.
        
        Args:
            resource_name: Name of the resource
            event_type: Type of event (acquire, release, operation)
            duration: Optional duration of the operation in seconds
            status: Status of the operation (success, warning, error)
            details: Optional additional details about the event
        """
        log_context = {
            'resource': resource_name,
            'event': event_type,
            'status': status
        }
        
        if duration is not None:
            log_context['duration'] = f"{duration:.6f}s"
        
        if details:
            log_context['details'] = details
        
        # Choose log level based on status
        if status == 'error':
            self.error("Resource %(resource)s %(event)s failed", **log_context)
        elif status == 'warning':
            self.warning("Resource %(resource)s %(event)s completed with warnings", **log_context)
        else:
            self.info("Resource %(resource)s %(event)s completed successfully", **log_context)


def get_logger(
    name: str = "resource_manager",
    level: int = logging.INFO,
    use_colors: Optional[bool] = None,
    structured_output: bool = False,
    log_file: Optional[str] = None,
) -> ResourceManagerLogger:
    """
    Factory function to create a resource manager logger.
    
    Args:
        name: Name of the logger
        level: Initial logging level
        use_colors: Whether to use colored output (auto-detected if None)
        structured_output: Whether to output logs in JSON format
        log_file: Optional file to write logs to
        
    Returns:
        ResourceManagerLogger: Configured logger
    """
    return ResourceManagerLogger(
        name=name,
        level=level,
        use_colors=use_colors,
        structured_output=structured_output,
        log_file=log_file
    )