"""Shared constants for the xsoar_client package."""

XSOAR_OLD_VERSION = 6
HTTP_CALL_TIMEOUT = 30

# Page size requested when fetching investigation entries via POST /investigation/<id>.
# Set high so that all War Room entries are returned in a single response.
INVESTIGATION_PAGE_SIZE = 1000
