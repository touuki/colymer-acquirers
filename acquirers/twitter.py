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

    @staticmethod
    def append_attachment(attachments, media):
        url = urlparse(media['media_url_https'])
        attachments.append({
            'id': media['id_str'],
            'filename': posixpath.basename(url.path),
            'content_type': 'image/jpeg',
            'original_url': media['media_url_https'],
            'metadata': media['original_info'],
            'persist_info': {
                'directly_transfer': True,
                'path': url.path,
                'referer': 'https://twitter.com',
            }
        })

        if 'video_info' in media:
            video = None
            for variant in media['video_info']['variants']:
                if variant['content_type'] == 'video/mp4' and (
                        video is None or variant['bitrate'] > video['bitrate']):
                    video = variant

            url = urlparse(video['url'])
            metadata = {
                'aspect_ratio': media['video_info']['aspect_ratio']
            }
            if video['bitrate'] > 0:
                metadata['bitrate'] = video['bitrate']
            if 'duration_millis' in media['video_info']:
                metadata['duration_millis'] = media['video_info']['duration_millis']
            if 'additional_media_info' in media and 'title' in media['additional_media_info']:
                metadata['title'] = media['additional_media_info']['title']

            attachments.append({
                'id': media['id_str'],
                'filename': posixpath.basename(url.path),
                'content_type': video['content_type'],
                'original_url': video['url'],
                'metadata': metadata,
                'persist_info': {
                    'directly_transfer': True,
                    'path': url.path,
                    'referer': 'https://twitter.com',
                }
            })

    def post_tweet(self, tweet):
        metadata = {
            'original_data': tweet
        }

        attachments = []

        if 'extended_entities' in tweet['legacy']:
            for media in tweet['legacy']['extended_entities']['media']:
                metadata['type'] = media['type']
                Twitter.append_attachment(attachments, media)

        if 'quoted_status' in tweet:
            metadata['quoted_status_id'] = tweet['quoted_status']['rest_id']
            metadata['type'] = 'quote'

        if 'in_reply_to_status_id_str' in tweet['legacy']:
            metadata['in_reply_to_status_id'] = tweet['legacy']['in_reply_to_status_id_str']
            metadata['type'] = 'reply'

        if 'retweeted_status' in tweet['legacy']:
            metadata['retweeted_status_id'] = tweet['legacy']['retweeted_status']['rest_id']
            metadata['type'] = 'retweet'

        article = {
            'author': {
                'id': tweet['legacy']['user_id_str'],
                'name': tweet['core']['user']['legacy']['screen_name']
            },
            'content_type': 'text/plain',
            'content': tweet['legacy']['full_text'],
            'title': '[{}] {}'.format(tweet['legacy']['lang'], tweet['core']['user']['legacy']['name']),
            'id': tweet['legacy']['id_str'],
            'original_url': 'https://twitter.com/{}/status/{}/'.format(
                tweet['core']['user']['legacy']['screen_name'], tweet['legacy']['id_str']),
            'time': datetime.strptime(tweet['legacy']['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
            'metadata': metadata
        }
        if attachments:
            article['attachments'] = attachments

        self.colymer.post_article(self.collection, article, overwrite=False)

    def process_tweet(self, tweet):
        if 'quoted_status' in tweet:
            self.process_tweet(tweet['quoted_status'])

        if 'legacy' in tweet:

            if 'retweeted_status' in tweet['legacy']:
                self.process_tweet(tweet['legacy']['retweeted_status'])

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

        data = self.twitter.user_tweets_and_replies(user_id, cursor=cursor)
        instructions = data['data']['user']['result']['timeline']['timeline']['instructions']
        entries = []
        count = 0
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
                count += 1

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

        if count == 0:
            result['has_next'] = False
            result['bottom_cursor'] = None

        time.sleep(self.request_interval)
        return result
