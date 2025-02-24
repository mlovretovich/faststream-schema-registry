from collections import OrderedDict
from datetime import datetime


class TimedLRUCache:
    def __init__(self, max_size=2, ttl=1):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl

    def __getitem__(self, key):
        if key not in self.cache:
            return None

        if (
            datetime.now() - self.cache[key]["added"]
        ).total_seconds() > self.ttl:
            del self.cache[key]
            return None

        self.cache.move_to_end(key)

        return self.cache[key]["value"]

    def __setitem__(self, key, value):
        self.cache[key] = {"value": value, "added": datetime.now()}

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
