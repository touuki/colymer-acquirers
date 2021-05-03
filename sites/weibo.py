from .site import Site
from getpass import getpass
import re
import json


class Weibo(Site):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.update_config()

    def load_cookies(self, path):
        super().load_cookies(path)
        self.update_config()

    def is_logined(self):
        return self.config['login']

    def logout(self):
        self.session.get('https://m.weibo.cn/logout',
                         headers={'Referer': 'https://m.weibo.cn/home/setting'})

    def login(self, username=None, password=None):
        if username is None:
            print('Please enter username:')
            username = input()
        if password is None:
            password = getpass('Please enter password: ')
        self.session.get(
            'https://passport.weibo.cn/signin/login?entry=mweibo&res=wel&wm=3349&r=https%3A%2F%2Fm.weibo.cn%2F')
        data = {
            'username': username,
            'password': password,
            'savestate': '1',
            'r': 'https://m.weibo.cn/',
            'ec': '0',
            'pagerefer': 'https://m.weibo.cn/',
            'entry': 'mweibo',
            'wentry': '',
            'loginfrom': '',
            'client_id': '',
            'code': '',
            'qq': '',
            'mainpageflag': '1',
            'hff': '',
            'hfp': ''
        }
        headers = {
            'Referer': 'https://passport.weibo.cn/signin/login?entry=mweibo&res=wel&wm=3349&r=https%3A%2F%2Fm.weibo.cn%2F'
        }
        response = self.session.post(
            'https://passport.weibo.cn/sso/login', data=data, headers=headers)
        if response.status_code != 200:
            raise Exception('sso login failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        result = response.json()
        if result['retcode'] != 50050011:
            raise Exception('sso login unexpected retcode. {} {} {}'.format(
                response.status_code, response.reason, result))

        response = self.session.get(
            result['data']['errurl'], headers=headers)
        search = re.search(
            r'phoneList\: JSON\.parse\(\'(.*)\'\)\,$', response.text, flags=re.M)
        phone = json.loads(search.group(1))[0]
        while True:
            print('Secondverify needed. You can: \n'
                  + '1. Send code to {} via SMS.\n'.format(phone['maskMobile'])
                    + '2. Send code to private message.\n'
                    + '3. I received the code, continue.\n'
                    + '4. Cancel login.')
            i = input()
            try:
                if i == '1':
                    msg_type = 'sms'
                    headers = {'Referer': response.url}
                    response = self.session.get('https://passport.weibo.cn/signin/secondverify/ajsend', params={
                        'number': phone['number'],
                        'mask_mobile': phone['maskMobile'],
                        'msg_type': msg_type
                    }, headers=headers)
                    if response.status_code != 200:
                        raise Exception('secondverify ajsend failed. {} {} {}'.format(
                            response.status_code, response.reason, response.text))
                    result = response.json()
                    if result['retcode'] != 100000:
                        raise Exception('secondverify ajsend failed. {} {} {}'.format(
                            response.status_code, response.reason, result))
                    response = self.session.get(
                        'https://passport.weibo.cn/signin/secondverify/check', headers=headers)
                elif i == '2':
                    msg_type = 'private_msg'
                    response = self.session.get('https://passport.weibo.cn/signin/secondverify/index', params={
                                                'way': msg_type}, headers={'Referer': response.url})
                    response = self.session.get('https://passport.weibo.cn/signin/secondverify/ajsend', params={
                        'msg_type': msg_type}, headers={'Referer': response.url})
                    if response.status_code != 200:
                        raise Exception('secondverify ajsend failed. {} {} {}'.format(
                            response.status_code, response.reason, response.text))
                    result = response.json()
                    if result['retcode'] != 100000:
                        raise Exception('secondverify ajsend failed. {} {} {}'.format(
                            response.status_code, response.reason, result))
                elif i == '3':
                    break
                elif i == '4':
                    return
            except Exception as e:
                print(e)

        while True:
            print('Please enter code:')
            code = input()
            response = self.session.get('https://passport.weibo.cn/signin/secondverify/ajcheck', params={
                'msg_type': msg_type,
                'code': code
            }, headers={
                'Referer': 'https://passport.weibo.cn/signin/secondverify/check'
            })
            if response.status_code != 200:
                raise Exception('secondverify check failed. {} {} {}'.format(
                    response.status_code, response.reason, response.text))
            result = response.json()
            if result['retcode'] == 100000:
                self.session.get(result['data']['url'], headers={
                                 'Referer': 'https://passport.weibo.cn/'})
                break
            elif result['retcode'] == 50050021:
                print('Maybe wrong code. Please enter again. {}'.format(
                    result))
            else:
                raise Exception('secondverify check failed. {} {} {}'.format(
                    response.status_code, response.reason, result))

        self.update_config()

    def update_config(self):
        self.session.get('https://weibo.com')
        headers = {
            'Referer': 'https://m.weibo.cn',
            'x-requested-with': 'XMLHttpRequest'
        }
        xsrf_token = self.session.cookies.get(
            'XSRF-TOKEN', domain='.m.weibo.cn')
        if xsrf_token:
            headers['x-xsrf-token'] = xsrf_token
        response = self.session.get(
            'https://m.weibo.cn/api/config', headers=headers, allow_redirects=False)
        if response.status_code != 200:
            raise Exception('config failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        result = response.json()
        if not result['ok']:
            raise Exception('config failed. {} {} {}'.format(
                response.status_code, response.reason, result))
        self.config = result['data']
        return self.config

    @staticmethod
    def pid2imgs(pid):
        """weibo.com接口不易获取图像URL的产物，现在使用m.weibo.cn的接口
        可以直接获取图像链接，就不再需要这个方法了。"""
        typ = 'gif' if pid[21] == 'g' else 'jpg'

        if pid[9] == 'w' or pid[9] == 'y' and len(pid) >= 32:
            """微博采用hash算法将pid映射到wx1,wx2,wx3,wx4四个子域名
            但是不知道是不是通用hash算法，位运算太麻烦了懒得写了
            反正四个子域名都能用，先这样吧"""
            s = "https://{}{}.sinaimg.cn/%s/{}.{}".format(
                'ww' if pid[9] == 'w' else 'wx', 1, pid, typ)
        else:
            s = "https://ss{}.sinaimg.cn/%s/{}&690".format(
                1+15 & int(pid[-2:], 16), pid)

        data = {
            'url': s % 'orj360',
            'large': {'url': s % 'large'},
            'webp': {'url': s % 'webp720'},
            'normal': {'url': s % 'mw1024'},
            'pid': pid,
            'type': typ
        }
        if len(pid) >= 32 and pid[22] >= '1':
            data['geo'] = {
                'width': int(pid[23:26], 36),
                'height': int(pid[26:29], 36)
            }

    def getIndex_timeline(self, uid, since_id=None, page=None):
        """正常返回10条（不包括置顶及其他），如果有不可见则不包括在内
        这样存在问题为如果有连续10条以上不可见，则扫描会中断
        从而无法判断是否真的扫描到底，官方的网页同样是此问题
        只能等官方api改进"""
        params = {
            'type': 'uid',
            'value': uid,
            'containerid': '107603{}'.format(uid)
        }
        if since_id is not None:
            params['since_id'] = since_id
        if page is not None:
            params['page'] = page
        headers = {
            'Referer': 'https://m.weibo.cn/u/{}'.format(uid),
            'x-requested-with': 'XMLHttpRequest'
        }
        xsrf_token = self.session.cookies.get(
            'XSRF-TOKEN', domain='.m.weibo.cn')
        if xsrf_token:
            headers['x-xsrf-token'] = xsrf_token
        response = self.session.get('https://m.weibo.cn/api/container/getIndex',
                                    params=params, headers=headers, allow_redirects=False)
        if response.status_code != 200:
            raise Exception('getIndex_timeline failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        result = response.json()
        if not result['ok'] and result['msg'] != '这里还没有内容':
            raise Exception('getIndex_timeline failed. {} {} {}'.format(
                response.status_code, response.reason, result))

        return result['data']

    def statuses_mymblog(self, uid, page):
        """由于m.weibo.cn的接口更方便图像链接、快转等的获取，
        并且其时间戳问题已被官方修复，因此此方法不再维护。
        正常返回20条，已知在好友圈可见等情况下返回数量小于20"""
        params = {
            'uid': uid,
            'page': page,
            'feature': '0'
        }
        headers = {
            'Referer': 'https://weibo.com/u/{}'.format(uid),
            'x-requested-with': 'XMLHttpRequest'
        }
        xsrf_token = self.session.cookies.get('XSRF-TOKEN', domain='weibo.com')
        if xsrf_token:
            headers['x-xsrf-token'] = xsrf_token
        response = self.session.get('https://weibo.com/ajax/statuses/mymblog',
                                    params=params, headers=headers, allow_redirects=False)
        if response.status_code != 200:
            raise Exception('statuses_mymblog failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        result = response.json()
        if not result['ok']:
            raise Exception('statuses_mymblog failed. {} {} {}'.format(
                response.status_code, response.reason, result))

        return result['data']

    def detail(self, mid):
        #response = self.session.get('https://m.weibo.cn/status/{}'.format(mid))
        response = self.session.get('https://m.weibo.cn/detail/{}'.format(mid))
        if not response.ok:
            raise Exception('detail failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))

        search = re.search(
            r'var \$render_data = \[([\s\S]*)\]\[0\] \|\| {};', response.text)
        if search:
            return json.loads(search.group(1))
        else:
            return None
