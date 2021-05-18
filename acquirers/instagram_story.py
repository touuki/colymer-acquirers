from datetime import datetime
import posixpath
import time
from urllib.parse import urlparse


class InstagramStory:
    def __init__(self, colymer, instagram, collection, request_interval=10):
        self.colymer = colymer
        self.instagram = instagram
        self.collection = collection
        self.request_interval = request_interval

    def scan(self, user_id):
        print('reels_media: user_id:{}'.format(user_id))
        data = self.instagram.reels_media(user_id)

        if data is not None:
            for item in data['items']:
                url = urlparse(item['image_versions2']['candidates'][0]['url'])
                attachments = [{
                    'id': item['id'],
                    'filename': posixpath.basename(url.path),
                    'content_type': 'image/jpeg',
                    'original_url': item['image_versions2']['candidates'][0]['url'],
                    'metadata': {
                        'width': item['image_versions2']['candidates'][0]['width'],
                        'height': item['image_versions2']['candidates'][0]['height']
                    },
                    'persist_info': {
                        'directly_transfer': True,
                        'path': url.path,
                        'referer': 'https://www.instagram.com/',
                    }
                }]

                if 'video_versions' in item:
                    url = urlparse(item['video_versions'][0]['url'])
                    attachments.append({
                        'id': item['video_versions'][0]['id'],
                        'filename': posixpath.basename(url.path),
                        'content_type': 'video/mp4',
                        'original_url': item['video_versions'][0]['url'],
                        'metadata': {
                            'width': item['video_versions'][0]['width'],
                            'height': item['video_versions'][0]['height'],
                            'duration_millis': int(item['video_duration'] * 1000)
                        },
                        'persist_info': {
                            'directly_transfer': True,
                            'path': url.path,
                            'referer': 'https://www.instagram.com/',
                        }
                    })

                self.colymer.post_article(self.collection, {
                    'author': {
                        'id': str(data['user']['pk']),
                        'name': data['user']['username']
                    },
                    'content_type': 'text/plain',
                    'content': '',
                    'title': item['code'],
                    'id': item['pk'],
                    'original_url': 'https://www.instagram.com/stories/{}/{}/'.format(data['user']['username'], item['pk']),
                    'time': datetime.fromtimestamp(item['taken_at']).isoformat() + 'Z',
                    'attachments': attachments,
                    'metadata': {
                        'original_data': item
                    }
                }, overwrite=False)

        time.sleep(self.request_interval)
