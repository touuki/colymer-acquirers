import time
import requests
import pickle
from functools import wraps


class Site:
    def __init__(self, headers=None, proxies=None, cookies=None, request_interval=0):
        self.session = requests.Session()
        if proxies is not None:
            self.session.proxies.update(proxies)
        if headers is not None:
            self.session.headers.update(headers)
        if cookies is not None:
            self.session.cookies.update(cookies)
        self.request_interval = request_interval
        self.request_last_timestamp = 0

    @staticmethod
    def request_wrapper(fn):
        @wraps(fn)
        def wrapper(self: Site, *args, **kwargs):
            should_sleep_time = self.request_last_timestamp + \
                self.request_interval - time.time()
            if should_sleep_time > 0:
                time.sleep(should_sleep_time)
            self.request_last_timestamp = time.time()
            print('{}: args:{} kwargs:{}'.format(fn.__name__, args, kwargs))
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
