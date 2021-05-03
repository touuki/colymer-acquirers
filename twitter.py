import requests
from sites import Twitter, Colymer
from common import Scanner, get_cookies
from datetime import datetime
from urllib.parse import urlparse
import time
import os
import posixpath

user_ids = ['1279429216015011841', '911494401087569920']
cookie_file = os.path.join(os.path.dirname(__file__), 'cookies/twitter.cookie')

twitter = Twitter(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    proxies={
        'http': 'http://localhost:7070',
        'https': 'http://localhost:7070',
    },
    cookies=get_cookies(cookie_file)
)

pin = None


def post_tweet(scanner, tweet):
    if 'legacy' in tweet:
        # TODO
        _id = None
        return _id
    else:
        return None


def process_tweet(scanner, tweet):
    if 'quoted_status' in tweet:
        # 引用推文
        post_tweet(scanner, tweet['quoted_status'])

    if 'legacy' in tweet and 'retweeted_status' in tweet['legacy']:
        if 'quoted_status' in tweet['legacy']['retweeted_status']:
            # 转推引用推文
            post_tweet(scanner, tweet['legacy']
                       ['retweeted_status']['quoted_status'])

        # 转推
        post_tweet(scanner, tweet['legacy']['retweeted_status'])

    return post_tweet(scanner, tweet)


def user_tweets_and_replies_handle(scanner, user_id, cursor, min_id):
    result = {
        'top': {
            'id': None,
            '_id': None
        },
        'last_id': None,
        'end_cursor': None,
        'has_next_page': True,
        'less_than_min_id': False
    }

    print('user_tweets_and_replies: user_id:{} cursor:{}'.format(user_id, cursor))
    data = twitter.user_tweets_and_replies(user_id, cursor=cursor)
    instructions = data['data']['user']['result']['timeline']['timeline']['instructions']
    entries = []
    for instruction in instructions:
        if instruction['type'] == 'TimelineAddEntries':
            entries = instruction['entries']
        if instruction['type'] == 'TimelinePinEntry':
            tweet = instruction['entry']['content']['itemContent']['tweet']
            if pin is None or pin['rest_id'] != tweet['rest_id']:
                process_tweet(scanner, tweet)
                pin = tweet

    for entry in entries:
        if entry['entryId'].startswith('tweet-'):
            tweet = entry['content']['itemContent']['tweet']

            if min_id is not None and int(entry['sortIndex']) <= int(min_id):
                result['less_than_min_id'] = True
                continue

            _id = process_tweet(scanner, tweet)
            if _id is not None:
                if result['top']['id'] is None or int(result['top']['id']) < int(entry['sortIndex']):
                    result['top']['id'] = entry['sortIndex']
                    result['top']['_id'] = _id

            result['last_id'] = entry['sortIndex']

        elif entry['entryId'].startswith('homeConversation-'):
            if min_id is not None and int(entry['sortIndex']) <= int(min_id):
                result['less_than_min_id'] = True
                continue

            for item in entry['content']['items']:
                tweet = item['item']['itemContent']['tweet']

                _id = process_tweet(scanner, tweet)
                if tweet['rest_id'] == entry['sortIndex'] and _id is not None:
                    if result['top']['id'] is None or int(result['top']['id']) < int(entry['sortIndex']):
                        result['top']['id'] = entry['sortIndex']
                        result['top']['_id'] = _id

            result['last_id'] = entry['sortIndex']

        elif entry['entryId'].startswith('cursor-bottom-'):
            result['end_cursor'] = entry['content']['value']

    assert result['end_cursor']
    if result['end_cursor'] == cursor:
        result['has_next_page'] = False
    return result


scanner = Scanner(
    colymer=Colymer('http://192.168.30.1:3000/api/'),
    collection='twitter',
    handle=user_tweets_and_replies_handle,
    request_interval=60
)

if __name__ == "__main__":
    try:
        for user_id in user_ids:
            scanner.user_timeline(user_id)

    finally:
        twitter.save_cookies(cookie_file)
