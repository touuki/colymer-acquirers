from .acquirer import Acquirer
from datetime import datetime
from urllib.parse import urlparse
import posixpath
import sites


class Instagram(Acquirer):
    def __init__(self, colymer: sites.Colymer, instagram: sites.Instagram, collection: str):
        super().__init__(colymer)
        self.instagram = instagram
        self.collection = collection

    @staticmethod
    def append_attachment(attachments, child_node):
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
                'referer': 'https://www.instagram.com/',
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
                    'referer': 'https://www.instagram.com/',
                }
            })

    def get_chain_id(self, user_id):
        return 'instagram-user-{}-timeline'.format(user_id)

    def acquire(self, cursor, min_id, user_id):
        result = {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True,
            'less_than_min_id': False
        }

        data = self.instagram.owner_to_timeline_media(user_id, after=cursor)

        result['bottom_cursor'] = data['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
        result['has_next'] = data['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']

        edges = data['user']['edge_owner_to_timeline_media']['edges']

        for edge in edges:
            node = edge['node']
            if min_id is not None and int(node['id']) <= int(min_id):
                result['less_than_min_id'] = True
                break

            attachments = []

            if node['__typename'] == 'GraphSidecar':
                for child_edge in node['edge_sidecar_to_children']['edges']:
                    Instagram.append_attachment(
                        attachments, child_edge['node'])
            else:
                Instagram.append_attachment(attachments, node)

            self.colymer.post_article(self.collection, {
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

            if result['top_id'] is None:
                result['top_id'] = node['id']

            result['bottom_id'] = node['id']

        return result
