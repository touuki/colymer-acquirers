import requests
from sites import Weibo, Colymer
from datetime import datetime
import time
import os
import pickle

request_interval = 60
uids = ['1856555760']
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
        print('[UNKNOWN CONDITION] "detail" does not seem to be accessible. mid:{}'.format(mid))
        return None
    
def post_status(status):
    attachments = []
    if 'pics' in status:
        for pic in status['pics']:
            attachments.append({
                'id': pic['pid'],
                'original_url': pic['large']['url'],
                'metadata': {
                    'width': int(pic['geo']['width']),
                    'height': int(pic['geo']['height'])
                }
            })
    if 'page_info' in status and status['page_info']['type'] == 'video':
        # TODO attachments.append
        pass
    
    metadata = {
        'original_data': status
    }
    if 'retweeted_status' in status:
        metadata['retweeted_status_id'] = status['retweeted_status']['mid']
        
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

def getIndex_timeline_handle(uid, since_id=None, min_id=None, max_id=None):
    print('getIndex_timeline: uid:{} since_id:{}'.format(uid, since_id))
    data = weibo.getIndex_timeline(uid, since_id=since_id)
    large_than_max_id = False
    less_than_min_id = False
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
        if 'isTop' not in status:
            if min_id is not None and int(status['mid']) <= int(min_id):
                less_than_min_id = True
                break
            if max_id is not None and int(status['mid']) >= int(max_id):
                large_than_max_id = True
                continue

        if 'retweeted_status' in status:
            retweeted_status = status['retweeted_status']
            if retweeted_status['user']:
                if retweeted_status['pic_num'] > 9:
                    single_data = weibo.detail(retweeted_status['mid'])
                    retweeted_status = single_data['status']

                _id = post_status(retweeted_status)
                _ids.append(_id)
            else:
                # 各种原因博文不可见（getIndex这个api除自己微博外不会返回已删除的转发），已知有：已删除、半年可见
                print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                    status['mid'], status['bid'], retweeted_status['mid'], retweeted_status['text']))

        if status['pic_num'] > 9:
            single_data = weibo.detail(status['mid'])
            status = single_data['status']
        
        _id = post_status(status)
        _ids.append(_id)

    return {
        '_ids': _ids,
        'count': len(data['cards']),
        'since_id': since_id,
        'has_next_page': has_next_page,
        'large_than_max_id': large_than_max_id,
        'less_than_min_id': less_than_min_id
    }

if False:
#if __name__ == "__main__":
    try:
        for uid in uids:
            pass

    finally:
        weibo.save_cookies(cookie_file)
