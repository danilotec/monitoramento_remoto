import redis

class RedisDataBase:
    def __init__(self, host: str = 'localhost', port: int = 6379,
                 db: int = 0, password: str | None = None) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password

    def connect_redis(self) -> redis.Redis:
        self.client = redis.Redis(
                            self.host, self.port,
                            self.db, self.password)
        return self.client