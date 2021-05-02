import requests
from sites import Twitter, Colymer
from datetime import datetime
from urllib.parse import urlparse
import time
import os
import pickle
import posixpath

request_interval = 60
user_ids = ['1279429216015011841', '911494401087569920']
collection = 'twitter'
cookie_file = os.path.join(os.path.dirname(__file__), 'cookies/twitter.cookie')
cookies = None
if os.path.exists(cookie_file):
    with open(cookie_file, 'rb') as f:
        cookies = pickle.load(f)

twitter = Twitter(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    proxies={
        'http': 'http://localhost:7070',
        'https': 'http://localhost:7070',
    },
    cookies=cookies
)
colymer = Colymer('http://192.168.30.1:3000/api/')
