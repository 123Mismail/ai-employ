class VaultSyncError(Exception):
    """Raised when git pull/push fails after all retries."""


class CrossDeviceMoveError(Exception):
    """Raised when source and destination are on different filesystems."""


class ApprovalExpiredError(Exception):
    """Raised when an approval file's expires timestamp has passed."""


class OdooConnectionError(Exception):
    """Raised when Odoo XML-RPC connection fails after all retries."""
