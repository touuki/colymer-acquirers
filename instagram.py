import requests
from sites import Instagram, Colymer
from datetime import datetime
from urllib.parse import urlparse
import time
import os
import posixpath

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
    print('owner_to_timeline_media: user_id:{} cursor:{}'.format(user_id, cursor))
    data = instagram.owner_to_timeline_media(user_id, after=cursor)
    page_info = data['user']['edge_owner_to_timeline_media']['page_info']
    edges = data['user']['edge_owner_to_timeline_media']['edges']
    large_than_max_id = False
    less_than_min_id = False
    last_id = None
    top = {
        'id': None,
        '_id': None
    }

    for edge in edges:
        node = edge['node']
        if min_id is not None and int(node['id']) <= int(min_id):
            less_than_min_id = True
            break
        if max_id is not None and int(node['id']) >= int(max_id):
            large_than_max_id = True
            continue

        attachments = []

        def append_attachment(child_node):
            url = urlparse(child_node['display_url'])
            attachments.append({
                'id': child_node['id'],
                'filename': posixpath.basename(url.path),
                'content_type': 'image/jpeg',
                'original_url': child_node['display_url'],
                'metadata': child_node['dimensions'],
                'persist_info': {
                    'directly_transfer': True,
                    'path': url.path,
                    'referer': 'https://www.instagram.com/{}/'.format(node['owner']['username']),
                }
            })
            if child_node['is_video']:
                url = urlparse(child_node['video_url'])
                attachments.append({
                    'id': child_node['id'],
                    'filename': posixpath.basename(url.path),
                    'content_type': 'video/mp4',
                    'original_url': child_node['video_url'],
                    'metadata': child_node['dimensions'],
                    'persist_info': {
                        'directly_transfer': True,
                        'path': url.path,
                        'referer': 'https://www.instagram.com/{}/'.format(node['owner']['username']),
                    }
                })

        if node['__typename'] == 'GraphSidecar':
            for child_edge in node['edge_sidecar_to_children']['edges']:
                append_attachment(child_edge['node'])
        else:
            append_attachment(node)

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
        }, overwrite=False)

        if top['id'] is None or int(top['id']) < int(node['id']):
            top['id'] = node['id']
            top['_id'] = _id

        last_id = node['id']

    return {
        'top': top,
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
                if block and (not result['top']['id'] or int(result['top']['id']) <= int(block['id'])):
                    top = block['_id']
                    bottom = block['bottom']
                    break
                elif result['top']['id']:
                    top = result['top']['_id']
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
