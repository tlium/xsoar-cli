from __future__ import annotations

import os

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from packaging import version

from .base import BaseArtifactProvider


class AzureArtifactProvider(BaseArtifactProvider):
    """Azure Blob Storage artifact provider."""

    def __init__(self, *, storage_account_url: str, container_name: str, access_token: str = "") -> None:
        self.storage_account_url = storage_account_url
        self.container_name = container_name
        self.access_token = access_token
        self._service = None
        self._container_client = None

    @property
    def service(self) -> BlobServiceClient:
        if self._service is None:
            if not self.access_token:
                access_token = os.environ.get("AZURE_STORAGE_SAS_TOKEN", "")
                if not access_token:
                    msg = "Cannot find access token. Either set the environment variable AZURE_STORAGE_SAS_TOKEN or call the constructor with the access_token argument set"
                    raise RuntimeError(msg)
                self.access_token = access_token
            self._service = BlobServiceClient(account_url=self.storage_account_url, credential=self.access_token)
        return self._service

    @property
    def container_client(self):
        if self._container_client is None:
            self._container_client = self.service.get_container_client(self.container_name)
        return self._container_client

    def test_connection(self) -> bool:
        self.container_client.get_container_properties()
        return True

    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        key_name = self.get_pack_path(pack_id, pack_version)
        blob_client = self.container_client.get_blob_client(blob=key_name)
        try:
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        key_name = self.get_pack_path(pack_id, pack_version)
        download_stream = self.container_client.download_blob(blob=key_name)
        return download_stream.readall()

    def get_latest_version(self, pack_id: str) -> str:
        prefix = f"content/packs/{pack_id}/"
        iter_names = self.container_client.list_blob_names(name_starts_with=prefix)
        version_list = [x.split("/")[3] for x in list(iter_names)]
        return str(max(version_list, key=version.parse))
