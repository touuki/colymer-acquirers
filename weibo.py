import requests
from sites import Weibo
from datetime import datetime
import time
import os
import pickle

request_interval = 60
collection = 'weibo'
cookie_file = os.path.join(os.path.dirname(__file__), 'cookies/weibo.cookie')
cookies = None
if os.path.exists(cookie_file):
    with open(cookie_file, 'rb') as f:
        cookies = pickle.load(f)

weibo = Weibo(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    cookies=cookies
)

