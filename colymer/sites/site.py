import os
import time
import requests
import pickle
from datetime import datetime
from functools import wraps


class Site:
    def __init__(self, headers=None, proxies=None, cookie_path=None, timeout=None, request_interval: float = 0):
        self.session = requests.Session()
        if proxies is not None:
            self.session.proxies.update(proxies)
        if headers is not None:
            self.session.headers.update(headers)

        self.cookie_path = cookie_path
        self.timeout = timeout

        if self.cookie_path is not None and os.path.exists(self.cookie_path):
            self.load_cookies(self.cookie_path)

        self.request_interval = request_interval
        self.request_last_timestamp = 0

    def close(self):
        if self.cookie_path is not None:
            self.save_cookies(self.cookie_path)

    @staticmethod
    def request_wrapper(fn):
        @wraps(fn)
        def wrapper(self: Site, *args, **kwargs):
            should_sleep_time = self.request_last_timestamp + \
                self.request_interval - time.time()
            if should_sleep_time > 0:
                time.sleep(should_sleep_time)
            self.request_last_timestamp = time.time()
            print('[{} request] {}: args:{} kwargs:{}'.format(datetime.now().isoformat(), fn.__name__, args, kwargs))
            return fn(self, *args, **kwargs)
        return wrapper

    def save_cookies(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def load_cookies(self, path):
        with open(path, 'rb') as f:
            self.session.cookies.update(pickle.load(f))

    def is_logined(self):
        return True

    def login(self):
        pass
