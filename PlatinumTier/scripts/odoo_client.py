import logging
import os
import xmlrpc.client
from functools import wraps
import time

from PlatinumTier.scripts.exceptions import OdooConnectionError

logger = logging.getLogger(__name__)


def _with_retry(max_attempts: int = 3, base_delay: float = 2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise OdooConnectionError(
                            f"Odoo call failed after {max_attempts} attempts: {e}"
                        ) from e
                    logger.warning("Odoo call failed (attempt %d): %s — retrying in %.1fs", attempt + 1, e, delay)
                    time.sleep(delay)
                    delay *= 2
        return wrapper
    return decorator


@_with_retry(max_attempts=3)
def connect(url: str = None, db: str = None, user: str = None, password: str = None):
    """
    Connect to Odoo via XML-RPC.
    Returns (models_proxy, uid) tuple.
    """
    url = url or os.environ["ODOO_URL"]
    db = db or os.environ["ODOO_DB"]
    user = user or os.environ["ODOO_USER"]
    password = password or os.environ["ODOO_PASSWORD"]

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise OdooConnectionError("Odoo authentication failed — check credentials")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    logger.info("Odoo connected — uid=%d db=%s", uid, db)
    return models, uid, db, password
