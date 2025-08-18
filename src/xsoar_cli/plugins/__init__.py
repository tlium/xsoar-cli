"""
XSOAR CLI Plugin System

This module provides the infrastructure for creating and loading plugins
for the xsoar-cli application. Plugins can extend the CLI with custom
commands and functionality.
"""

from abc import ABC, abstractmethod
from typing import Optional

import click


class XSOARPlugin(ABC):
    """
    Abstract base class for XSOAR CLI plugins.

    All plugins should inherit from this class and implement the required methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the plugin version."""

    @property
    def description(self) -> Optional[str]:
        """Return an optional description of the plugin."""
        return None

    @abstractmethod
    def get_command(self) -> click.Command:
        """
        Return the Click command or command group that this plugin provides.

        Returns:
            click.Command: The command to be registered with the CLI
        """

    def initialize(self) -> None:
        """
        Initialize the plugin. Called once when the plugin is loaded.
        Override this method if your plugin needs initialization.
        """

    def cleanup(self) -> None:
        """
        Cleanup plugin resources. Called when the application shuts down.
        Override this method if your plugin needs cleanup.
        """


class PluginError(Exception):
    """Exception raised when there's an error with plugin loading or execution."""


class PluginLoadError(PluginError):
    """Exception raised when a plugin fails to load."""


class PluginRegistrationError(PluginError):
    """Exception raised when a plugin fails to register."""
