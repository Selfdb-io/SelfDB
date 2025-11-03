"""Configuration management package for SelfDB."""

from .config_manager import ConfigManager, ConfigValidationError

__all__ = ['ConfigManager', 'ConfigValidationError']