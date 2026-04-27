from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.environments import RATE_LIMIT_DEFAULT, RATE_LIMIT_REDIS_ENABLED, RATE_LIMIT_REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=RATE_LIMIT_REDIS_URL if RATE_LIMIT_REDIS_ENABLED else "memory://",
)
