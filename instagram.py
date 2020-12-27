import requests
from sites import Instagram, Colymer
from datetime import datetime
import time
import os

request_interval = 60
user_ids = ['39817910000']
collection = 'instagram'
cookie_file = os.path.join(os.path.dirname(
    __file__), 'cookies/instagram.cookie')
instagram = Instagram(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    proxies={
        'http': 'http://localhost:17070',
        'https': 'http://localhost:17070',
    }
)
colymer = Colymer('http://localhost:3000/api/')


def owner_to_timeline_media(user_id, cursor=None, min_id=None, max_id=None):
    data = instagram.owner_to_timeline_media(user_id, after=cursor)
    page_info = data['user']['edge_owner_to_timeline_media']['page_info']
    edges = data['user']['edge_owner_to_timeline_media']['edges']

    _ids = []
    for edge in edges:
        node = edge['node']
        if min_id is not None and int(node['id']) <= int(min_id) or max_id is not None and int(node['id']) >= int(max_id):
            continue

        attachments = []
        if node['__typename'] == 'GraphSidecar':
            for child_edge in node['edge_sidecar_to_children']['edges']:
                child_node = child_edge['node']
                attachments.append({
                    'id': child_node['id'],
                    'original_url': child_node['display_url'],
                    'metadata': child_node['dimensions']
                })
                if child_node['is_video']:
                    attachments.append({
                        'id': child_node['id'],
                        'original_url': child_node['video_url'],
                        'metadata': child_node['dimensions']
                    })
        else:
            attachments.append({
                'id': node['id'],
                'original_url': node['display_url'],
                'metadata': node['dimensions']
            })
            if node['is_video']:
                attachments.append({
                    'id': node['id'],
                    'original_url': node['video_url'],
                    'metadata': node['dimensions']
                })

        _id = colymer.post_article(collection, {
            'author': {
                'id': node['owner']['id'],
                'name': node['owner']['username']
            },
            'content_type': 'text/plain',
            'content': node['edge_media_to_caption']['edges'][0]['node']['text'] if node['edge_media_to_caption']['edges'] else '',
            'title': node['shortcode'],
            'id': node['id'],
            'original_url': 'https://www.instagram.com/p/{}/'.format(node['shortcode']),
            'time': datetime.fromtimestamp(node['taken_at_timestamp']).isoformat() + 'Z',
            'attachments': attachments,
            'metadata': {
                'original_data': node,
                'cursor': cursor,
                'end_cursor': page_info['end_cursor']
            }
        }, replace=True)

        _ids.append(_id)

    return {
        '_ids': _ids,
        'edges_count': len(edges),
        'end_cursor': page_info['end_cursor'],
        'has_next_page': page_info['has_next_page']
    }


if os.path.exists(cookie_file):
    instagram.load_cookies(cookie_file)

try:
    for user_id in user_ids:
        data = colymer.get_articles(collection, [
            {'$match': {'author.id': user_id, 'metadata.top': True}},
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
    instagram.save_cookies(cookie_file)
