import requests
from sites import Weibo, Colymer
from datetime import datetime
import time
import os
import pickle

request_interval = 3
user_ids = ['5825014417']
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
colymer = Colymer('http://localhost:3000/api/')


def fast_retweeted_handle(mid):
    data = weibo.detail(mid)
    if data is None:
        print(
            '[UNKNOWN CONDITION] "detail" does not seem to be accessible. mid:{}'.format(mid))
        return None


def post_status(status, source):
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
                attachments.append({
                    'id': pic['pid'],
                    'original_url': pic['large']['url'],
                    'metadata': {
                        'width': int(pic['geo']['width']),
                        'height': int(pic['geo']['height'])
                    }
                })
        if 'page_info' in status:
            metadata['type'] = status['page_info']['type']
            if status['page_info']['type'] == 'video':
                # TODO attachments.append
                pass
            elif status['page_info']['type'] == 'article':
                # TODO attachments.append 一例：since_id=4559721145047710 
                pass

        article = {
            'author': {
                'id': status['user']['id'],
                'name': status['user']['screen_name']
            },
            'content_type': 'text/html',
            'content': status['text'],
            'title': status['bid'],
            'id': status['mid'],
            'original_url': 'https://m.weibo.cn/detail/{}'.format(status['bid']),
            'time': datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
            'attachments': attachments,
            'metadata': metadata
        }
        if 'edit_count' in status:
            article['version'] = status['edit_count']
    return colymer.post_article(collection, article, replace=False)


def getIndex_timeline_handle(user_id, since_id=None, min_id=None, max_id=None):
    print('getIndex_timeline: user_id:{} since_id:{}'.format(user_id, since_id))
    data = weibo.getIndex_timeline(user_id, since_id=since_id)
    large_than_max_id = False
    less_than_min_id = False
    last_id = None
    if 'cardlistInfo' in data and 'since_id' in data['cardlistInfo']:
        since_id = data['cardlistInfo']['since_id']
        has_next_page = True
    else:
        since_id = None
        has_next_page = False

    _ids = []
    for card in data['cards']:
        if card['card_type'] != 9:
            continue
        status = card['mblog']
        if 'isTop' not in status or not status['isTop']:
            if min_id is not None and int(status['mid']) <= int(min_id):
                less_than_min_id = True
                break
            if max_id is not None and int(status['mid']) >= int(max_id):
                large_than_max_id = True
                continue

        if 'retweeted_status' in status:
            retweeted_status = status['retweeted_status']
            if retweeted_status['user']:
                if retweeted_status['pic_num'] > 9 or retweeted_status['isLongText']:
                    time.sleep(request_interval)
                    single_data = weibo.detail(retweeted_status['mid'])
                    retweeted_status = single_data['status']

                _id = post_status(retweeted_status, 'm.weibo.cn')
                _ids.append(_id)
            else:
                # 各种原因博文不可见，已知有：已删除（getIndex这个api除自己微博外不会返回已删除的转发）、半年可见、无权限
                print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                    status['mid'], status['bid'], retweeted_status['mid'], retweeted_status['text']))

        if status['pic_num'] > 9 or status['isLongText']:
            time.sleep(request_interval)
            single_data = weibo.detail(status['mid'])
            status = single_data['status']

        _id = post_status(status, 'm.weibo.cn')
        _ids.append(_id)
        last_id = status['mid']

    return {
        '_ids': _ids,
        'last_id': last_id,
        'count': len(data['cards']),
        'since_id': since_id,
        'has_next_page': has_next_page,
        'large_than_max_id': large_than_max_id,
        'less_than_min_id': less_than_min_id
    }


def get_block(user_id, max_id=None):
    match = {'author.id': user_id, 'metadata.bottom': {'$exists': True}}
    if max_id is not None:
        match['id'] = {'$lt': max_id}
    data = colymer.get_articles(collection, [
        {'$match': match},
        {'$sort': {'id': -1}},
        {'$limit': 1},
        {'$project': {
            '_id': 1,
            'id': 1,
            'bottom': '$metadata.bottom'
        }}
    ], collation={
        'locale': 'en_US',
        'numericOrdering': True
    })

    if data:
        return data[0]
    else:
        return None


def set_block_bottom(_id, bottom):
    colymer.put_article(collection, _id, {
                        '$set': {'metadata.bottom': bottom}})


def scan_user(user_id):
    top = None
    bottom = {
        'id': None,
        'since_id': None
    }
    max_id = None
    min_id = None
    while True:
        block = get_block(user_id, max_id)
        min_id = block['id'] if block else None
        while True:
            time.sleep(request_interval)
            result = getIndex_timeline_handle(
                user_id, since_id=bottom['since_id'], min_id=min_id)

            if top is None:
                if result['_ids']:
                    top = result['_ids'][0]
                elif block is not None:
                    assert result['less_than_min_id']
                    top = block['_id']
                    bottom = block['bottom']
                    break
                else:
                    print('Seem no data for user_id:{}.'.format(user_id))
                    return

            if result['less_than_min_id']:
                bottom = block['bottom']
                set_block_bottom(top, bottom)
                break

            if not result['has_next_page']:
                if result['last_id'] is not None:
                    bottom = {
                        'id': result['last_id'],
                        'since_id': None
                    }
                    set_block_bottom(top, bottom)
                    break
                else:
                    print('Seem scan interrupt for user_id:{} since_id:{} last_id:{}.'.format(
                        user_id, bottom['since_id'], bottom['id']))
                    return

            bottom = {
                'id': result['last_id'],
                'since_id': result['since_id']
            }
            set_block_bottom(top, bottom)

        if bottom['since_id'] is None:
            break
        max_id = block['bottom']['id']


if False:
    # if __name__ == "__main__":
    try:
        for user_id in user_ids:
            scan_user(user_id)

    finally:
        weibo.save_cookies(cookie_file)
