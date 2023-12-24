from ..sites import ColymerSite, WeiboSite
from .acquirer import Acquirer
from datetime import datetime
from urllib.parse import urlparse
import posixpath


class WeiboAcquirer(Acquirer):
    def __init__(self, colymer: ColymerSite, weibo: WeiboSite, collection: str):
        super().__init__(colymer)
        self.weibo = weibo
        self.collection = collection

    @staticmethod
    def append_video_m(attachments: list, page_info):
        if page_info['urls'] is None:
            return
        
        if 'mp4_720p_mp4' in page_info['urls']:
            quality = '720P'
            directly_transfer = page_info['media_info']['duration'] < 2400
            url_str = page_info['urls']['mp4_720p_mp4']
        elif 'mp4_hd_mp4' in page_info['urls']:
            quality = '480P'
            directly_transfer = page_info['media_info']['duration'] < 4800
            url_str = page_info['urls']['mp4_hd_mp4']
        elif 'mp4_ld_mp4' in page_info['urls']:
            quality = '360P'
            directly_transfer = page_info['media_info']['duration'] < 9600
            url_str = page_info['urls']['mp4_ld_mp4']

        url = urlparse(url_str)
        attachments.append({
            'id': page_info['object_id'],
            'filename': posixpath.basename(url.path),
            'content_type': 'video/mp4',
            'original_url': url_str,
            'metadata': {
                'duration_millis': int(page_info['media_info']['duration'] * 1000),
                'quality': quality
            },
            'persist_info': {
                'directly_transfer': directly_transfer,
                'path': url.path,
                'referer': 'https://m.weibo.cn/',
            }
        })

    @staticmethod
    def append_video(attachments: list, page_info):
        if 'media_info' not in page_info:
            return
        media_info = page_info['media_info']
        quality_index = 0
        if 'playback_list' in media_info:
            for playback in media_info['playback_list']:
                if playback['meta']['type'] == 1 and playback['meta']['quality_index'] > quality_index:
                    quality_index = playback['meta']['quality_index']
                    play_info = playback['play_info']

        if quality_index:
            url = urlparse(play_info['url'])
            attachments.append({
                'id': page_info['object_id'],
                'filename': posixpath.basename(url.path),
                'content_type': play_info['mime'],
                'original_url': play_info['url'],
                'metadata': {
                    'duration_millis': int(play_info['duration'] * 1000),
                    'width': play_info['width'],
                    'height': play_info['height'],
                    'size': play_info['size'],
                    'bitrate': play_info['bitrate']
                },
                'persist_info': {
                    # 300MB
                    'directly_transfer': play_info['size'] < 314572800,
                    'path': url.path,
                    'referer': 'https://weibo.com/',
                }
            })
        else:
            if media_info['mp4_720p_mp4']:
                quality = '720P'
                directly_transfer = media_info['duration'] < 2400
                url_str = media_info['mp4_720p_mp4']
            elif media_info['mp4_hd_url']:
                quality = '480P'
                directly_transfer = media_info['duration'] < 4800
                url_str = media_info['mp4_hd_url']
            elif media_info['mp4_sd_url']:
                quality = '360P'
                directly_transfer = media_info['duration'] < 9600
                url_str = media_info['mp4_sd_url']

            url = urlparse(url_str)
            attachments.append({
                'id': page_info['object_id'],
                'filename': posixpath.basename(url.path),
                'content_type': 'video/mp4',
                'original_url': url_str,
                'metadata': {
                    'duration_millis': int(media_info['duration'] * 1000),
                    'quality': quality
                },
                'persist_info': {
                    'directly_transfer': directly_transfer,
                    'path': url.path,
                    'referer': 'https://weibo.com/',
                }
            })

    @staticmethod
    def append_pics_m(attachments: list, pic):
        url = urlparse(pic['large']['url'])
        attachments.append({
            'id': pic['pid'],
            'filename': posixpath.basename(url.path),
            'content_type': 'image/gif' if url.path[-3:] == 'gif' else 'image/jpeg',
            'original_url': pic['large']['url'],
            'metadata': {
                'width': int(pic['geo']['width']),
                'height': int(pic['geo']['height'])
            },
            'persist_info': {
                'directly_transfer': True,
                'path': url.path,
                'referer': 'https://m.weibo.cn/',
            }
        })

    @staticmethod
    def append_pics(attachments: list, pic):
        url = urlparse(pic['largest']['url'])
        attachments.append({
            'id': pic['pic_id'],
            'filename': posixpath.basename(url.path),
            'content_type': 'image/gif' if url.path[-3:] == 'gif' else 'image/jpeg',
            'original_url': pic['largest']['url'],
            'metadata': {
                'width': int(pic['largest']['width']),
                'height': int(pic['largest']['height'])
            },
            'persist_info': {
                'directly_transfer': True,
                'path': url.path,
                'referer': 'https://weibo.com/',
            }
        })

    def post_status(self, status, source):
        """需注意情况：置顶，9图以上，长微博，快转，视频，文章"""
        if source == 'weibo.com':
            metadata = {
                'source': source,
                'type': 'text'
            }

            if 'screen_name_suffix_new' in status and len(status['screen_name_suffix_new']) == 4:
                metadata['quick_forward'] = {
                    'username': status['screen_name_suffix_new'][2]['content'],
                    'mid': status['mid'],
                }
                status = self.weibo.statuses_show(status['mblogid'])

            # 20230604: 似乎9图以上可以全部返回了，不再需要以下代码
            #if status['pic_num'] and ('pic_infos' not in status or len(status['pic_infos']) < status['pic_num']):
            #    status = self.weibo.statuses_show(status['mblogid'])

            # weibo.com的isLongText在图片多于9个时也会返回true，无法判断长微博
            if status['isLongText'] and status['textLength'] > 280:
                text = self.weibo.statuses_longtext(status['mblogid'])
                status['longTextContent'] = text
            else:
                text = status['text_raw']

            metadata['original_data'] = status

            attachments = []
            if 'pic_infos' in status:
                metadata['type'] = 'picture'
                if 'pic_ids' in status:
                    for pid in status['pic_ids']:
                        self.append_pics(
                            attachments, status['pic_infos'][pid])
                else:
                    # 有page_info的情况下单个图片可能会缩成查看图片
                    for struct in status['url_struct']:
                        if struct['url_title'] == '查看图片':
                            for pid in struct['pic_ids']:
                                self.append_pics(
                                    attachments, struct['pic_infos'][pid])

            if 'mix_media_info' in status:
                metadata['type'] = 'mix'
                for item in status['mix_media_info']['items']:
                    if item['type'] == 'video':
                        self.append_video(attachments, item['data'])
                    elif item['type'] == 'pic':
                        self.append_pics(attachments, item['data'])

            if 'page_info' in status and 'object_type' in status['page_info']:
                metadata['type'] = status['page_info']['object_type']
                if status['page_info']['object_type'] == 'video':
                    self.append_video(attachments, status['page_info'])

                elif status['page_info']['object_type'] == 'article':
                    # TODO 放到新的collection中
                    pass

            if 'retweeted_status' in status:
                metadata['type'] = 'retweet'
                metadata['retweeted_status_id'] = status['retweeted_status']['mid']

            article = {
                'author': {
                    'id': str(status['user']['id']),
                    'name': status['user']['screen_name']
                },
                'content_type': 'text/plain',
                'content': text,
                'title': status['mblogid'],
                'id': status['mid'],
                'original_url': 'https://weibo.com/{}/{}'.format(status['user']['id'], status['mblogid']),
                'time': datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
                'metadata': metadata
            }
            if attachments:
                article['attachments'] = attachments
            if 'edit_count' in status:
                article['version'] = status['edit_count']

            self.colymer.post_article(
                self.collection, article, overwrite=False)
        elif source == 'm.weibo.cn':
            metadata = {
                'original_data': status,
                'source': source,
                'type': 'text'
            }

            attachments = []
            if 'pics' in status:
                metadata['type'] = 'picture'
                for pic in status['pics']:
                    self.append_pics_m(attachments, pic)

            if 'page_info' in status:
                metadata['type'] = status['page_info']['type']
                if status['page_info']['type'] == 'video':
                    self.append_video_m(attachments, status['page_info'])

                elif status['page_info']['type'] == 'article':
                    # TODO 放到新的collection中 一例：since_id=4559721145047710
                    pass

            if 'retweeted_status' in status:
                metadata['type'] = 'retweet'
                metadata['retweeted_status_id'] = status['retweeted_status']['mid']

            article = {
                'author': {
                    'id': str(status['user']['id']),
                    'name': status['user']['screen_name']
                },
                'content_type': 'text/html',
                'content': status['text'],
                'title': status['bid'],
                'id': status['mid'],
                'original_url': 'https://m.weibo.cn/detail/{}'.format(status['bid']),
                'time': datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat(),
                'metadata': metadata
            }
            if attachments:
                article['attachments'] = attachments
            if 'edit_count' in status:
                article['version'] = status['edit_count']

            self.colymer.post_article(
                self.collection, article, overwrite=False)

    def get_chain_id(self, user_id, q=None):
        return 'weibo-user-{}-timeline'.format(user_id) if q is None else 'weibo-user-{}-searchblog-{}'.format(user_id, q)

    def acquire(self, page, min_id, user_id, q=None):
        result = {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True,
            'less_than_min_id': False
        }

        if page is None:
            page = 1

        if q is None:
            data = self.weibo.statuses_mymblog(user_id, page)
        else:
            data = self.weibo.profile_searchblog(user_id, page, q)

        if len(data['list']):
            result['bottom_cursor'] = page + 1
            result['has_next'] = True
        else:
            result['bottom_cursor'] = None
            result['has_next'] = False

        for status in data['list']:
            if 'isTop' not in status or not status['isTop']:
                if min_id is not None and int(status['mid']) <= int(min_id):
                    result['less_than_min_id'] = True
                    break

                if result['top_id'] is None:
                    result['top_id'] = status['mid']

                result['bottom_id'] = status['mid']

            if 'retweeted_status' in status:
                retweeted_status = status['retweeted_status']
                #新版微博会把转发的page_info移出来，真坑爹
                if 'page_info' in status:
                    retweeted_status['page_info'] = status['page_info']
                    del status['page_info']

                if retweeted_status['user']:
                    self.post_status(retweeted_status, 'weibo.com')
                else:
                    # 各种原因博文不可见，已知有：已删除（getIndex这个api除自己微博外不会返回已删除的转发）、半年可见、无权限
                    print('"user" in retweeted_status is null. mid:{} bid:{} retweeted_mid:{} retweeted_text:{}'.format(
                        status['mid'], status['mblogid'], retweeted_status['mid'], retweeted_status['text']))

            self.post_status(status, 'weibo.com')

        return result
