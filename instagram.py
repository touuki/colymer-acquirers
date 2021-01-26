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


def owner_to_timeline_media_handle(user_id, cursor=None, min_id=None, max_id=None):
    data = instagram.owner_to_timeline_media(user_id, after=cursor)
    page_info = data['user']['edge_owner_to_timeline_media']['page_info']
    edges = data['user']['edge_owner_to_timeline_media']['edges']
    large_than_max_id = False
    less_than_min_id = False

    _ids = []
    for edge in edges:
        node = edge['node']
        if min_id is not None and int(node['id']) <= int(min_id):
            less_than_min_id = True
            break
        if max_id is not None and int(node['id']) >= int(max_id):
            large_than_max_id = True
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
        }, replace=False)

        _ids.append(_id)

    return {
        '_ids': _ids,
        'edges_count': len(edges),
        'end_cursor': page_info['end_cursor'],
        'has_next_page': page_info['has_next_page'],
        'large_than_max_id': large_than_max_id,
        'less_than_min_id': less_than_min_id
    }


def get_block(max_id=None):
    match = {'author.id': user_id, 'metadata.bottom__id': {'$exists': True}}
    if max_id is not None:
        match['id'] = {'$lt': max_id}
    data = colymer.get_articles(collection, [
        {'$match': match},
        {'$sort': {'id': -1}},
        {'$limit': 1},
        {'$project': {
            'top__id': '$_id',
            'top_id': '$id',
            'bottom__id': '$metadata.bottom__id'
        }}
    ], collation={
        'locale': 'en_US',
        'numericOrdering': True
    })

    result = {
        'top__id': None,
        'top_id': None,
        'bottom__id': None,
        'bottom_id': None,
        'end_cursor': None
    }
    if data:
        result['top__id'] = data[0]['top__id']
        result['top_id'] = data[0]['top_id']
        result['bottom__id'] = data[0]['bottom__id']
        if data[0]['bottom__id'] is not None:
            data = colymer.get_article(collection, result['bottom__id'], projection={
                'metadata.end_cursor': 1,
                'id': 1
            })
            result['bottom_id'] = data['id']
            result['end_cursor'] = data['metadata']['end_cursor']

    return result


def set_block_pointer(top__id, bottom__id):
    colymer.put_article(collection, top__id, {
                        '$set': {'metadata.bottom__id': bottom__id}})


def scan_user(user_id):
    top__id = None
    bottom__id = None
    max_id = None
    min_id = None
    cursor = None
    while True:
        block = get_block(max_id)
        min_id = block['top_id']
        while True:
            result = owner_to_timeline_media_handle(
                user_id, cursor=cursor, min_id=min_id)
            time.sleep(request_interval)

            if top__id is None:
                if result['_ids']:
                    top__id = result['_ids'][0]
                elif block['top__id'] is not None:
                    assert result['less_than_min_id']
                    top__id = block['top__id']
                    bottom__id = block['bottom__id']
                    cursor = block['end_cursor']
                    break
                else:
                    return

            if result['less_than_min_id']:
                bottom__id = block['bottom__id']
                cursor = block['end_cursor']
                set_block_pointer(top__id, bottom__id)
                break

            if not result['has_next_page']:
                bottom__id = None
                set_block_pointer(top__id, bottom__id)
                break

            if result['_ids']:
                bottom__id = result['_ids'][-1]
                set_block_pointer(top__id, bottom__id)

            cursor = result['end_cursor']

        if bottom__id is None:
            break
        max_id = block['bottom_id']


if os.path.exists(cookie_file):
    instagram.load_cookies(cookie_file)

if __name__ == "__main__":
    try:
        for user_id in user_ids:
            scan_user(user_id)

    finally:
        instagram.save_cookies(cookie_file)
