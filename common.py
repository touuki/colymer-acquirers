import time
import os
import pickle


def get_cookies(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    else:
        return None


def _handle(scanner, user_id, cursor, min_id):
    """handle接口说明"""
    return {
        'top': {
            'id': None,
            '_id': None
        },
        'last_id': '',
        'end_cursor': '',
        'has_next_page': True,
        'less_than_min_id': False
    }


class Scanner:
    def __init__(self, colymer, collection, handle, request_interval=3):
        self.colymer = colymer
        self.collection = collection
        self._handle = handle
        self.request_interval = request_interval

    def _get_block(self, user_id, max_id=None):
        match = {'author.id': user_id, 'metadata.bottom': {'$exists': True}}
        if max_id is not None:
            match['id'] = {'$lt': max_id}
        data = self.colymer.get_articles(self.collection, [
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

    def _set_block_bottom(self, _id, bottom):
        self.colymer.put_article(self.collection, _id, {
                                 '$set': {'metadata.bottom': bottom}})

    def post_article(self, article):
        return self.colymer.post_article(self.collection, article, overwrite=False)

    def user_timeline(self, user_id):
        top__id = None
        bottom = {
            'id': None,
            'cursor': None,
            'bottom': False
        }
        max_id = None
        min_id = None
        while True:
            # 获取最近的一个数据块
            block = self._get_block(user_id, max_id)
            min_id = block['id'] if block else None
            # 开始段落扫描
            while not bottom['bottom']:
                result = self._handle(self, user_id, bottom['cursor'], min_id)
                time.sleep(self.request_interval)

                # 第一次拉取
                if top__id is None:
                    # 如果存在既往数据，与既往数据比较获取最大的id
                    if block and (not result['top']['id'] or int(result['top']['id']) <= int(block['id'])):
                        # 无更新的数据，使用既往数据块，结束段落扫描
                        top__id = block['_id']
                        bottom = block['bottom']
                        break
                    elif result['top']['id']:
                        # 开启新段落
                        top__id = result['top']['_id']
                    else:
                        # 无数据，退出
                        print('Seem no data for user_id:{}.'.format(user_id))
                        return

                if result['less_than_min_id']:
                    # 该段落扫描结束
                    bottom = block['bottom']
                    self._set_block_bottom(top__id, bottom)
                    break

                if not result['has_next_page']:
                    # 扫描到底，退出
                    bottom['bottom'] = True

                if result['last_id'] is not None:
                    bottom['id'] = result['last_id']
                if result['end_cursor'] is None:
                    # 如果cursor为空，则必须退出扫描
                    assert bottom['bottom']
                bottom['cursor'] = result['end_cursor']
                self._set_block_bottom(top__id, bottom)

            if bottom['bottom']:
                break
            max_id = block['bottom']['id']
