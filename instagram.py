import requests
from sites import Instagram, Colymer
from common import Scanner, get_cookies
from datetime import datetime
from urllib.parse import urlparse
import time
import os
import posixpath

user_ids = ['39817910000']
cookie_file = os.path.join(os.path.dirname(
    __file__), 'cookies/instagram.cookie')

instagram = Instagram(
    headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    },
    proxies={
        'http': 'http://localhost:17070',
        'https': 'http://localhost:17070',
    },
    cookies=get_cookies(cookie_file)
)


def owner_to_timeline_media_handle(scanner, user_id, cursor, min_id):
    print('owner_to_timeline_media: user_id:{} cursor:{}'.format(user_id, cursor))
    data = instagram.owner_to_timeline_media(user_id, after=cursor)
    page_info = data['user']['edge_owner_to_timeline_media']['page_info']
    edges = data['user']['edge_owner_to_timeline_media']['edges']
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

        _id = scanner.post_article({
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
        })

        if top['id'] is None or int(top['id']) < int(node['id']):
            top['id'] = node['id']
            top['_id'] = _id

        last_id = node['id']

    return {
        'top': top,
        'last_id': last_id,
        'end_cursor': page_info['end_cursor'],
        'has_next_page': page_info['has_next_page'],
        'less_than_min_id': less_than_min_id
    }


scanner = Scanner(
    colymer=Colymer('http://192.168.30.1:3000/api/'),
    collection='instagram',
    handle=owner_to_timeline_media_handle,
    request_interval=60
)

if __name__ == "__main__":
    try:
        for user_id in user_ids:
            scanner.user_timeline(user_id)

    finally:
        instagram.save_cookies(cookie_file)
