"""Plugin infrastructure for extending the CLI with custom commands."""

from __future__ import annotations

from abc import ABC, abstractmethod

import click


class XSOARPlugin(ABC):
    """Base class for CLI plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the plugin version."""

    @property
    def description(self) -> str | None:
        """Return an optional description of the plugin."""
        return None

    @abstractmethod
    def get_command(self) -> click.Command:
        """Return the Click command or group that this plugin provides."""

    def initialize(self) -> None:
        """Initialize the plugin. Called once when the plugin is loaded.

        Override this method if your plugin needs initialization.
        """


class PluginError(Exception):
    """Base exception for plugin errors."""


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""


class PluginRegistrationError(PluginError):
    """Raised when a plugin fails to register its command."""
