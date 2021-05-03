from sites import Weibo, Colymer
from common import Scanner, get_cookies
from datetime import datetime
from urllib.parse import urlparse
import time
import os
import posixpath

user_ids = ['5825014417']
cookie_file = os.path.join(os.path.dirname(__file__), 'cookies/weibo.cookie')

weibo = Weibo(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    cookies=get_cookies(cookie_file)
)


def post_status(scanner, status, source):
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
    return scanner.post_article(article)


def getIndex_timeline_handle(scanner, user_id, since_id, min_id):
    print('getIndex_timeline: user_id:{} since_id:{}'.format(user_id, since_id))
    data = weibo.getIndex_timeline(user_id, since_id=since_id)
    less_than_min_id = False
    last_id = None
    top = {
        'id': None,
        '_id': None
    }
    if 'cardlistInfo' in data and 'since_id' in data['cardlistInfo']:
        since_id = data['cardlistInfo']['since_id']
        has_next_page = True
    else:
        since_id = None
        has_next_page = False

    for card in data['cards']:
        if card['card_type'] != 9:
            continue
        status = card['mblog']
        if 'isTop' not in status or not status['isTop']:
            if min_id is not None and int(status['mid']) <= int(min_id):
                less_than_min_id = True
                break

        if 'retweeted_status' in status:
            retweeted_status = status['retweeted_status']
            if retweeted_status['user']:
                if retweeted_status['pic_num'] > 9 or retweeted_status['isLongText']:
                    time.sleep(scanner.request_interval)
                    single_data = weibo.detail(retweeted_status['mid'])
                    retweeted_status = single_data['status']

                post_status(scanner, retweeted_status, 'm.weibo.cn')
            else:
                # 各种原因博文不可见，已知有：已删除（getIndex这个api除自己微博外不会返回已删除的转发）、半年可见、无权限
                print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                    status['mid'], status['bid'], retweeted_status['mid'], retweeted_status['text']))

        if status['pic_num'] > 9 or status['isLongText']:
            time.sleep(scanner.request_interval)
            single_data = weibo.detail(status['mid'])
            status = single_data['status']

        _id = post_status(scanner, status, 'm.weibo.cn')

        if top['id'] is None or int(top['id']) < int(status['mid']):
            top['id'] = status['mid']
            top['_id'] = _id

        last_id = status['mid']

    return {
        'top': top,
        'last_id': last_id,
        'end_cursor': since_id,
        'has_next_page': has_next_page,
        'less_than_min_id': less_than_min_id
    }


scanner = Scanner(
    colymer=Colymer('http://192.168.30.1:3000/api/'),
    collection='weibo',
    handle=getIndex_timeline_handle,
    request_interval=3
)

# if False:
if __name__ == "__main__":
    try:
        if not weibo.is_logined():
            weibo.login()
        for user_id in user_ids:
            scanner.user_timeline(user_id)

    finally:
        weibo.save_cookies(cookie_file)
