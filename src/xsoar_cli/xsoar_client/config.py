from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ClientConfig:
    """Configuration for XSOAR Client."""

    server_version: int
    custom_pack_authors: list[str] = field(default_factory=list)
    api_token: str = ""
    server_url: str = ""
    xsiam_auth_id: str = ""
    verify_ssl: bool | str = False

    def __post_init__(self) -> None:
        """Load credentials from environment if not provided."""
        if not self.api_token or not self.server_url:
            self._load_from_env()
        self._validate()

    def _load_from_env(self) -> None:
        """Load credentials from environment variables."""
        self.api_token = self.api_token or os.getenv("DEMISTO_API_KEY", "")
        self.server_url = self.server_url or os.getenv("DEMISTO_BASE_URL", "")
        self.xsiam_auth_id = self.xsiam_auth_id or os.getenv("XSIAM_AUTH_ID", "")

    def _validate(self) -> None:
        """Validate configuration."""
        if not self.api_token or not self.server_url:
            raise ValueError("Both api_token and server_url are required")
