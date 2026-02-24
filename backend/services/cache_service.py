class CacheService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
            cls._instance._cache = {}
            cls._instance._ttls = {}
        return cls._instance

    def get(self, key: str):
        import time
        if key in self._ttls and time.time() > self._ttls[key]:
            del self._cache[key]
            del self._ttls[key]
            return None
        return self._cache.get(key)
    
    def set(self, key: str, value, ttl: int = 86400):
        import time
        self._cache[key] = value
        self._ttls[key] = time.time() + ttl
    
    def exists(self, key: str) -> bool:
        return self.get(key) is not None

# Global Singleton
cache = CacheService()
