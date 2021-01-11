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
    

def statuses_mymblog_handle(uid, page=None, min_id=None, max_id=None):
    print('statuses_mymblog: uid:{} page:{}'.format(uid, page))
    data = weibo.statuses_mymblog(uid, page=page)
    large_than_max_id = False
    less_than_min_id = False

    _ids = []
    for status in data['list']:
        if min_id is not None and int(status['mid']) <= int(min_id):
            less_than_min_id = True
            break
        if max_id is not None and int(status['mid']) >= int(max_id):
            large_than_max_id = True
            continue

        if 'screen_name_suffix_new' in status:
            if len(status['screen_name_suffix_new']) >= 4 and status['screen_name_suffix_new'][3]['content'] == '快转了':
                _id = fast_retweeted_handle(status['mid'])
                if _id is not None:
                    _ids.append(_id)
            else:
                print('[UNKNOWN CONDITION] "screen_name_suffix_new" in status. mid:{} status:{}'.format(
                    status['mid'], status))
            continue

        if 'deleted' in status:
            # 已知情况为自己账号快转被删除，因此判断快转要在这之前
            print('[UNKNOWN CONDITION] Find "deleted" in status. mid:{}'.format(
                status['mid']))
            continue

        attachments = []
        if status['__typename'] == 'GraphSidecar':
            for child_edge in status['edge_sidecar_to_children']['edges']:
                child_status = child_edge['status']
                attachments.append({
                    'id': child_status['id'],
                    'original_url': child_status['display_url'],
                    'metadata': child_status['dimensions']
                })
                if child_status['is_video']:
                    attachments.append({
                        'id': child_status['id'],
                        'original_url': child_status['video_url'],
                        'metadata': child_status['dimensions']
                    })
        else:
            attachments.append({
                'id': status['id'],
                'original_url': status['display_url'],
                'metadata': status['dimensions']
            })
            if status['is_video']:
                attachments.append({
                    'id': status['id'],
                    'original_url': status['video_url'],
                    'metadata': status['dimensions']
                })

        metadata = {
            'original_data': status,
            'page': page
        }

        if 'retweeted_status' in status:
            metadata['retweeted_status_id'] = status['mid']
            retweeted_status = status['retweeted_status']
            if retweeted_status['user']:
                pass
            else:
                # 各种原因博文不可见，已知有：已删除、半年可见
                print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                    status['mid'], status['mblogid'], retweeted_status['mid'], retweeted_status['text_raw']))

        article = {
            'author': {
                'id': status['user']['id'],
                'name': status['user']['screen_name']
            },
            'content_type': 'text/html',
            'content': status['text'],
            'title': status['mblogid'],
            'id': status['mid'],
            'original_url': 'https://weibo.com/{}/{}'.format(status['user']['id'], status['mblogid']),
            'time': datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
            'attachments': attachments,
            'metadata': metadata
        }
        if 'edit_count' in status:
            article['version'] = status['edit_count']
        _id = colymer.post_article(collection, article, replace=False)

        _ids.append(_id)

    return {
        '_ids': _ids,
        'count': len(data['list']),
        'large_than_max_id': large_than_max_id,
        'less_than_min_id': less_than_min_id
    }

if False:
#if __name__ == "__main__":
    try:
        for uid in uids:
            data = colymer.get_articles(collection, [
                {'$match': {'author.id': uid, 'metadata.top': True}},
                {'$sort': {'id': -1}},
                {'$limit': 1},
                {'$project': {'id': 1}}
            ], collation={
                'locale': 'en_US',
                'numericOrdering': True
            })

            if data:
                min_id = data[0]['id']
            else:
                min_id = None

            top_id = None
            cursor = None
            has_next_page = True
            while has_next_page:
                result = owner_to_timeline_media(
                    user_id, cursor=cursor, min_id=min_id)
                if top_id is None and result['_ids']:
                    top_id = result['_ids'][0]
                    colymer.put_article(
                        collection, top_id, {'$set': {'metadata.top': True}})
                has_next_page = result['has_next_page']
                cursor = result['end_cursor']
                time.sleep(request_interval)
                if len(result['_ids']) < result['edges_count']:
                    break

            if result['_ids'] and not has_next_page:
                colymer.put_article(
                    collection, result['_ids'][-1], {'$set': {'metadata.bottom': True}})

            data = colymer.get_articles(collection, [
                {'$match': {'author.id': user_id}},
                {'$sort': {'id': 1}},
                {'$limit': 1},
                {'$project': {
                    'id': 1,
                    'cursor': '$metadata.cursor',
                    'bottom': '$metadata.bottom'
                }}
            ], collation={
                'locale': 'en_US',
                'numericOrdering': True
            })

            if data and 'bottom' not in data[0]:
                max_id = data[0]['id']
                cursor = data[0]['cursor']
                has_next_page = True
                while has_next_page:
                    result = owner_to_timeline_media(
                        user_id, cursor=cursor, max_id=max_id)
                    has_next_page = result['has_next_page']
                    cursor = result['end_cursor']
                    time.sleep(request_interval)

                if result['_ids']:
                    colymer.put_article(
                        collection, result['_ids'][-1], {'$set': {'metadata.bottom': True}})
    finally:
        weibo.save_cookies(cookie_file)
