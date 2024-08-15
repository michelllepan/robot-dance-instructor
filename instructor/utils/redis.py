import redis

from ..utils import get_config

def make_redis_client():
    cfg = get_config()
    client = redis.Redis(
        host=cfg["redis"]["host"],
        port=cfg["redis"]["port"],
        decode_responses=True,
    )
    return client