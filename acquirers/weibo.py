import sites
from .acquirer import Acquirer
from datetime import datetime
from urllib.parse import urlparse
import posixpath


class Weibo(Acquirer):
    def __init__(self, colymer: sites.Colymer, weibo: sites.Weibo, collection: str):
        super().__init__(colymer)
        self.weibo = weibo
        self.collection = collection

    def post_status(self, status, source):
        if source == 'm.weibo.cn':
            metadata = {
                'original_data': status,
                'source': source,
                'type': 'text'
            }
            if 'retweeted_status' in status:
                metadata['type'] = 'retweet'
                metadata['retweeted_status_id'] = status['retweeted_status']['mid']

            attachments = []
            if 'pics' in status:
                metadata['type'] = 'picture'
                for pic in status['pics']:
                    url = urlparse(pic['large']['url'])
                    attachments.append({
                        'id': pic['pid'],
                        'filename': posixpath.basename(url.path),
                        'content_type': 'image/gif' if url.path[-3:] == 'gif' else 'image/jpeg',
                        'original_url': pic['large']['url'],
                        'metadata': {
                            'width': int(pic['geo']['width']),
                            'height': int(pic['geo']['height'])
                        },
                        'persist_info': {
                            'directly_transfer': True,
                            'path': url.path,
                            'referer': 'https://m.weibo.cn/u/{}'.format(status['user']['id']),
                        }
                    })
            if 'page_info' in status:
                metadata['type'] = status['page_info']['type']
                if status['page_info']['type'] == 'video':
                    # TODO 放到新的collection中
                    pass
                elif status['page_info']['type'] == 'article':
                    # TODO 放到新的collection中 一例：since_id=4559721145047710
                    pass

            article = {
                'author': {
                    'id': str(status['user']['id']),
                    'name': status['user']['screen_name']
                },
                'content_type': 'text/html',
                'content': status['text'],
                'title': status['bid'],
                'id': status['mid'],
                'original_url': 'https://m.weibo.cn/detail/{}'.format(status['bid']),
                'time': datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
                'metadata': metadata
            }
            if attachments:
                article['attachments'] = attachments
            if 'edit_count' in status:
                article['version'] = status['edit_count']

            self.colymer.post_article(
                self.collection, article, overwrite=False)

    def get_chain_id(self, user_id):
        return 'weibo-user-{}-timeline'.format(user_id)

    def acquire(self, since_id, min_id, user_id):
        result = {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True,
            'less_than_min_id': False
        }

        data = self.weibo.getIndex_timeline(user_id, since_id=since_id)

        if 'cardlistInfo' in data and 'since_id' in data['cardlistInfo']:
            result['bottom_cursor'] = str(data['cardlistInfo']['since_id'])
            result['has_next'] = True
        else:
            result['bottom_cursor'] = None
            result['has_next'] = False

        for card in data['cards']:
            if card['card_type'] != 9:
                continue
            status = card['mblog']
            if 'isTop' not in status or not status['isTop']:
                if min_id is not None and int(status['mid']) <= int(min_id):
                    result['less_than_min_id'] = True
                    break

                if result['top_id'] is None:
                    result['top_id'] = status['mid']

                result['bottom_id'] = status['mid']

            if 'retweeted_status' in status:
                retweeted_status = status['retweeted_status']
                if retweeted_status['user']:
                    if retweeted_status['pic_num'] > 9 or retweeted_status['isLongText']:
                        single_data = self.weibo.detail(
                            retweeted_status['mid'])
                        retweeted_status = single_data['status']

                    self.post_status(retweeted_status, 'm.weibo.cn')
                else:
                    # 各种原因博文不可见，已知有：已删除（getIndex这个api除自己微博外不会返回已删除的转发）、半年可见、无权限
                    print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                        status['mid'], status['bid'], retweeted_status['mid'], retweeted_status['text']))

            if status['pic_num'] > 9 or status['isLongText']:
                single_data = self.weibo.detail(status['mid'])
                status = single_data['status']

            self.post_status(status, 'm.weibo.cn')

        return result
