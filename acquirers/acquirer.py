import sites


class Acquirer:
    def __init__(self, colymer: sites.Colymer):
        self.colymer = colymer

    def scan(self, **kwargs):
        chain_id = self.get_chain_id(**kwargs)
        block = {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True
        }
        block_id = None
        max_top_id = None
        min_acquire_id = None
        while True:
            # 获取最近的一个数据块
            next_block = self.colymer.get_recent_block(chain_id, max_top_id=max_top_id)
            min_acquire_id = next_block['top_id'] if next_block else None
            # 开始段落扫描
            while block['has_next']:
                result = self.acquire(block['bottom_cursor'], min_acquire_id, **kwargs)

                # 第一次拉取
                if block['top_id'] is None:
                    # 如果存在既往数据，与既往数据比较获取最大的id
                    if next_block and (result['top_id'] is None or int(result['top_id']) <= int(next_block['top_id'])):
                        # 无更新的数据，使用既往数据块，结束段落扫描
                        block['top_id'] = next_block['top_id']
                        block['bottom_id'] = next_block['bottom_id']
                        block['bottom_cursor'] = next_block['bottom_cursor']
                        block['has_next'] = next_block['has_next']
                        block_id = next_block['_id']
                        break
                    elif result['top_id']:
                        # 开启新段落
                        block['top_id'] = result['top_id']
                    else:
                        # 无数据，退出
                        print('Seem no data for chain_id:{}.'.format(chain_id))
                        return

                if result['less_than_min_id']:
                    # 该段落扫描结束
                    block['bottom_id'] = next_block['bottom_id']
                    block['bottom_cursor'] = next_block['bottom_cursor']
                    block['has_next'] = next_block['has_next']
                    if block_id is None:
                        block_id = next_block['_id']
                    
                    self.colymer.put_block(chain_id, block_id, block)

                    if block_id != next_block['_id']:
                        self.colymer.delete_block(chain_id, next_block['_id'])
                    break

                block['has_next'] = result['has_next']

                if result['bottom_id'] is not None:
                    block['bottom_id'] = result['bottom_id']

                if result['bottom_cursor'] is None:
                    # 如果cursor为空，则必须退出扫描
                    assert not block['has_next']

                block['bottom_cursor'] = result['bottom_cursor']

                if block_id is None:
                    block_id = self.colymer.post_block(chain_id, block)
                else:
                    self.colymer.put_block(chain_id, block_id, block)

            if not block['has_next']:
                break
            max_top_id = block['bottom_id']

    def get_chain_id(self, **kwargs):
        return self.__class__.__name__

    def acquire(self, cursor, min_id, **kwargs):
        raise Exception('Method unimplemented.')
        return {
            'top_id': None,
            'bottom_id': None,
            'bottom_cursor': None,
            'has_next': True,
            'less_than_min_id': False
        }
