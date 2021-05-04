import requests
import pickle


class Site:
    def __init__(self, headers=None, proxies=None, cookies=None):
        self.session = requests.Session()
        if proxies is not None:
            self.session.proxies.update(proxies)
        if headers is not None:
            self.session.headers.update(headers)
        if cookies is not None:
            self.session.cookies.update(cookies)

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
