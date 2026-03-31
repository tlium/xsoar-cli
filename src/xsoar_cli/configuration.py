"""Configuration management for XSOAR CLI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.artifact_providers.azure import AzureArtifactProvider
    from xsoar_cli.xsoar_client.artifact_providers.s3 import S3ArtifactProvider
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentParams:
    """Parsed and validated parameters for a single XSOAR environment."""

    base_url: str
    api_token: str
    server_version: int
    verify_ssl: bool | str = True
    xsiam_auth_id: str = ""
    artifacts_location: str | None = None
    s3_bucket_name: str = ""
    azure_blobstore_url: str = ""
    azure_container_name: str = ""
    azure_storage_access_token: str = ""

    @classmethod
    def from_dict(cls, env_name: str, config: dict) -> EnvironmentParams:
        """Create EnvironmentParams from a raw config dict.

        Raises ValueError with a clear message if a required key is missing.
        """
        required_keys = ("base_url", "api_token", "server_version")
        for key in required_keys:
            if key not in config:
                msg = f"Environment '{env_name}' is missing required key '{key}'"
                raise ValueError(msg)

        return cls(
            base_url=config["base_url"],
            api_token=config["api_token"],
            server_version=config["server_version"],
            verify_ssl=config.get("verify_ssl", True),
            xsiam_auth_id=str(config.get("xsiam_auth_id", "")),
            artifacts_location=config.get("artifacts_location"),
            s3_bucket_name=config.get("s3_bucket_name", ""),
            azure_blobstore_url=config.get("azure_blobstore_url", ""),
            azure_container_name=config.get("azure_container_name", ""),
            azure_storage_access_token=config.get("azure_storage_access_token", ""),
        )


class EnvironmentConfig:
    """Configuration for a single XSOAR environment."""

    def __init__(self, env_name: str, config: dict, custom_pack_authors: list[str]):
        self.env_name = env_name
        self.params = EnvironmentParams.from_dict(env_name, config)
        self.custom_pack_authors = custom_pack_authors
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Lazy-load the XSOAR client."""
        if self._client is None:
            logger.debug("Creating XSOAR client for environment '%s'", self.env_name)
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Client:
        """Create the XSOAR client with artifact provider."""
        # Lazy import for performance reasons
        from xsoar_cli.xsoar_client.client import Client

        logger.debug(
            "Client config for '%s': server_version=%s, base_url=%s, verify_ssl=%s",
            self.env_name,
            self.params.server_version,
            self.params.base_url,
            self.params.verify_ssl,
        )

        artifact_provider = self._create_artifact_provider()
        logger.info("Initialized XSOAR client for environment '%s'", self.env_name)
        return Client(
            server_url=self.params.base_url,
            api_token=self.params.api_token,
            server_version=self.params.server_version,
            xsiam_auth_id=self.params.xsiam_auth_id,
            verify_ssl=self.params.verify_ssl,
            custom_pack_authors=self.custom_pack_authors,
            artifact_provider=artifact_provider,
        )

    def _create_artifact_provider(self) -> S3ArtifactProvider | AzureArtifactProvider | None:
        """Create the appropriate artifact provider based on config."""
        if self.params.artifacts_location == "S3":
            # Lazy import for performance reasons
            from xsoar_cli.xsoar_client.artifact_providers.s3 import S3ArtifactProvider

            logger.debug("Creating S3 artifact provider for '%s' (bucket: %s)", self.env_name, self.params.s3_bucket_name)
            return S3ArtifactProvider(bucket_name=self.params.s3_bucket_name)
        elif self.params.artifacts_location == "Azure":
            # Lazy import for performance reasons
            from xsoar_cli.xsoar_client.artifact_providers.azure import AzureArtifactProvider

            logger.debug("Creating Azure artifact provider for '%s'", self.env_name)
            return AzureArtifactProvider(
                storage_account_url=self.params.azure_blobstore_url,
                container_name=self.params.azure_container_name,
                access_token=self.params.azure_storage_access_token,
            )
        logger.debug("No artifact provider configured for '%s'", self.env_name)
        return None

    @property
    def has_artifact_provider(self) -> bool:
        """Check if this environment has an artifact provider configured."""
        return self.params.artifacts_location is not None


class XSOARConfig:
    """Main configuration object for XSOAR CLI."""

    def __init__(self, config_dict: dict):
        self.default_environment: str = config_dict["default_environment"]
        self.custom_pack_authors: list[str] = config_dict["custom_pack_authors"]
        self.default_new_case_type: str = config_dict["default_new_case_type"]

        # Build environment configs
        self._environments: dict[str, EnvironmentConfig] = {}
        for env_name, env_config in config_dict["server_config"].items():
            self._environments[env_name] = EnvironmentConfig(env_name, env_config, self.custom_pack_authors)
        logger.debug(
            "XSOARConfig initialized: default_environment='%s', environments=%s",
            self.default_environment,
            list(self._environments.keys()),
        )

    def get_client(self, environment: str | None = None) -> Client:
        """Get the XSOAR client for the specified environment (or default)."""
        return self.get_environment(environment).client

    def has_environment(self, environment: str) -> bool:
        """Check if an environment exists in the config."""
        return environment in self._environments

    @property
    def environment_names(self) -> list[str]:
        """Get list of all configured environment names."""
        return list(self._environments.keys())

    def environment_has_artifacts(self, environment: str | None = None) -> bool:
        """Check if an environment has artifact provider configured."""
        return self.get_environment(environment).has_artifact_provider

    def get_environment(self, environment: str | None = None) -> EnvironmentConfig:
        """Get the EnvironmentConfig for the specified environment (or default)."""
        env = environment or self.default_environment
        if env not in self._environments:
            raise ValueError(f"Unknown environment: {env}")
        return self._environments[env]
