from core.decorators import instance
from core.logger import Logger
from pathlib import Path
import os
import time


@instance()
class CacheService:
    CACHE_DIR = os.sep + os.path.join("data", "cache")

    def __init__(self):
        Path(os.getcwd() + self.CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.logger = Logger(__name__)

    def store(self, group, filename, contents):
        base_path = os.getcwd() + self.CACHE_DIR + os.sep + group
        Path(base_path).mkdir(exist_ok=True)

        with open(base_path + os.sep + filename, "w") as f:
            f.write(contents)

    def retrieve(self, group, filename, max_age=None):
        base_path = os.getcwd() + self.CACHE_DIR + os.sep + group

        full_path = base_path + os.sep + filename

        try:
            with open(full_path, "r") as f:
                last_modified = int(os.path.getmtime(full_path))
                if not max_age or int(time.time()) < last_modified + max_age:
                    return f.read()
                else:
                    return None
        except FileNotFoundError:
            return None
