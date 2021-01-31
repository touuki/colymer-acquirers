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
    last_id = None

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
                'original_data': node
            }
        }, replace=False)

        _ids.append(_id)
        last_id = node['id']

    return {
        '_ids': _ids,
        'last_id': last_id,
        'edges_count': len(edges),
        'end_cursor': page_info['end_cursor'],
        'has_next_page': page_info['has_next_page'],
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
        'end_cursor': None
    }
    max_id = None
    min_id = None
    while True:
        block = get_block(user_id, max_id)
        min_id = block['id'] if block else None
        while True:
            result = owner_to_timeline_media_handle(
                user_id, cursor=bottom['end_cursor'], min_id=min_id)
            time.sleep(request_interval)

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
                bottom = {
                    'id': result['last_id'],
                    'end_cursor': None
                }
                set_block_bottom(top, bottom)
                break

            bottom = {
                'id': result['last_id'],
                'end_cursor': result['end_cursor']
            }
            set_block_bottom(top, bottom)

        if bottom['end_cursor'] is None:
            break
        max_id = block['bottom']['id']


if os.path.exists(cookie_file):
    instagram.load_cookies(cookie_file)

if __name__ == "__main__":
    try:
        for user_id in user_ids:
            scan_user(user_id)

    finally:
        instagram.save_cookies(cookie_file)
