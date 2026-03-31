"""Version checking utilities for xsoar-cli."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packaging.version import Version

logger = logging.getLogger(__name__)

PACKAGE_NAME = "xsoar-cli"


def is_pypi_install(package_name: str) -> bool:
    """Check whether a package was installed from a package index (e.g. PyPI).

    Returns False for editable installs and other direct installs (VCS, local path).
    PEP 610: direct_url.json is present for any non-index install. Its absence
    means the package was installed from an index.
    """
    dist = importlib.metadata.distribution(package_name)
    return dist.read_text("direct_url.json") is None


def get_installed_version(package_name: str) -> Version:
    """Return the currently installed version of a package."""
    # Lazy import for performance reasons
    from packaging.version import Version

    dist = importlib.metadata.distribution(package_name)
    return Version(dist.version)


def get_latest_version(package_name: str) -> Version:
    """Fetch the latest stable version of a package from PyPI."""
    # Lazy import for performance reasons
    import requests
    from packaging.version import Version

    headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
    url = f"https://pypi.org/simple/{package_name}/"
    response = requests.get(url, headers=headers, timeout=3)
    response.raise_for_status()
    data = response.json()
    versions = sorted([Version(v) for v in data["versions"]])
    stable = [v for v in versions if not v.is_prerelease and not v.is_devrelease]
    return stable[-1] if stable else versions[-1]


def check_for_update(config_data: dict | None) -> str | None:
    """Check if a newer version of xsoar-cli is available on PyPI.

    Returns a message string if an update is available, None otherwise.
    Skips the check when skip_version_check is absent or True in the config,
    or when the package was not installed from an index.
    """
    # Default to skipping version check if config is missing or
    # skip_version_check is absent/True in the config.
    if not config_data or config_data.get("skip_version_check", True):
        logger.debug("Skipping version check (disabled in configuration)")
        return None

    pypi_install = is_pypi_install(PACKAGE_NAME)
    installed = get_installed_version(PACKAGE_NAME)
    logger.debug("Installed: %s, PyPI install: %s", installed, pypi_install)

    if not pypi_install:
        logger.debug("Skipping version check (not installed from PyPI)")
        return None

    latest = get_latest_version(PACKAGE_NAME)
    logger.debug("Latest on PyPI: %s", latest)

    if latest > installed:
        return f"Update available: {PACKAGE_NAME} {installed} -> {latest}"
    return None
