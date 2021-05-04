from .acquirer import Acquirer
from datetime import datetime
from urllib.parse import urlparse
import time
import posixpath


class Twitter(Acquirer):
    def __init__(self, colymer, twitter, collection, request_interval=15):
        super().__init__(colymer)
        self.twitter = twitter
        self.collection = collection
        self.request_interval = request_interval
        self.pin_ids = {}

    def post_tweet(self, tweet):
        if 'legacy' in tweet:
            # TODO
            _id = None
            return _id
        else:
            return None

    def process_tweet(self, tweet):
        if 'quoted_status' in tweet:
            # 引用推文
            self.post_tweet(tweet['quoted_status'])

        if 'legacy' in tweet and 'retweeted_status' in tweet['legacy']:
            if 'quoted_status' in tweet['legacy']['retweeted_status']:
                # 转推引用推文
                self.post_tweet(
                    tweet['legacy']['retweeted_status']['quoted_status'])

            # 转推
            self.post_tweet(tweet['legacy']['retweeted_status'])

        self.post_tweet(tweet)

    def get_chain_id(self, user_id):
        return 'twitter-user-{}-tweets_and_replies'.format(user_id)
    
    def acquire(self, cursor, min_id, user_id):
        print('user_tweets_and_replies: user_id:{} cursor:{}'.format(user_id, cursor))

        result = {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True,
            'less_than_min_id': False
        }

        data = twitter.user_tweets_and_replies(user_id, cursor=cursor)
        instructions = data['data']['user']['result']['timeline']['timeline']['instructions']
        entries = []
        for instruction in instructions:
            if instruction['type'] == 'TimelineAddEntries':
                entries = instruction['entries']
            if instruction['type'] == 'TimelinePinEntry':
                tweet = instruction['entry']['content']['itemContent']['tweet']
                if user_id not in self.pin_ids or self.pin_ids[user_id] != tweet['rest_id']:
                    self.process_tweet(tweet)
                    self.pin_ids[user_id] = tweet['rest_id']

        for entry in entries:
            if entry['entryId'].startswith('tweet-') or entry['entryId'].startswith('homeConversation-'):

                if min_id is not None and int(entry['sortIndex']) <= int(min_id):
                    result['less_than_min_id'] = True
                    continue

                if entry['entryId'].startswith('homeConversation-'):
                    for item in entry['content']['items']:
                        self.process_tweet(
                            item['item']['itemContent']['tweet'])
                else:
                    self.process_tweet(
                        entry['content']['itemContent']['tweet'])

                if result['top_id'] is None:
                    result['top_id'] = entry['sortIndex']

                result['bottom_id'] = entry['sortIndex']

            elif entry['entryId'].startswith('cursor-bottom-'):
                result['bottom_cursor'] = entry['content']['value']

        if result['bottom_cursor'] is None or result['bottom_cursor'] == cursor:
            result['has_next'] = False
        return result
