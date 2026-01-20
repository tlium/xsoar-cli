"""Configuration management for XSOAR CLI."""

from typing import Optional

from xsoar_client.artifact_providers.azure import AzureArtifactProvider
from xsoar_client.artifact_providers.s3 import S3ArtifactProvider
from xsoar_client.config import ClientConfig
from xsoar_client.xsoar_client import Client


class EnvironmentConfig:
    """Configuration for a single XSOAR environment."""

    def __init__(self, env_name: str, config: dict, custom_pack_authors: list[str]):
        self.env_name = env_name
        self._config = config
        self.custom_pack_authors = custom_pack_authors
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy-load the XSOAR client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Client:
        """Create the XSOAR client with artifact provider."""
        xsoar_client_config = ClientConfig(
            server_version=self._config["server_version"],
            custom_pack_authors=self.custom_pack_authors,
            api_token=self._config["api_token"],
            server_url=self._config["base_url"],
            xsiam_auth_id=self._config.get("xsiam_auth_id", ""),
            verify_ssl=self._config["verify_ssl"],
        )

        artifact_provider = self._create_artifact_provider()
        return Client(config=xsoar_client_config, artifact_provider=artifact_provider)

    def _create_artifact_provider(self):
        """Create the appropriate artifact provider based on config."""
        artifacts_location = self._config.get("artifacts_location")

        if artifacts_location == "S3":
            bucket_name = self._config.get("s3_bucket_name", "")
            return S3ArtifactProvider(bucket_name=bucket_name)
        elif artifacts_location == "Azure":
            return AzureArtifactProvider(
                storage_account_url=self._config["azure_blobstore_url"],
                container_name=self._config["azure_container_name"],
                access_token=self._config.get("azure_storage_access_token", ""),
            )
        return None

    @property
    def has_artifact_provider(self) -> bool:
        """Check if this environment has an artifact provider configured."""
        return self._config.get("artifacts_location") is not None


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

    def get_client(self, environment: Optional[str] = None) -> Client:
        """Get the XSOAR client for the specified environment (or default)."""
        env = environment or self.default_environment
        if env not in self._environments:
            raise ValueError(f"Unknown environment: {env}")
        return self._environments[env].client

    def has_environment(self, environment: str) -> bool:
        """Check if an environment exists in the config."""
        return environment in self._environments

    @property
    def environment_names(self) -> list[str]:
        """Get list of all configured environment names."""
        return list(self._environments.keys())

    def environment_has_artifacts(self, environment: Optional[str] = None) -> bool:
        """Check if an environment has artifact provider configured."""
        env = environment or self.default_environment
        return self._environments[env].has_artifact_provider
