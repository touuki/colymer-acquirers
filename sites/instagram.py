from .site import Site
from getpass import getpass
import json
import time


class Instagram(Site):
    # story url: Login required GET https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}

    def is_logined(self):
        response = self.session.get('https://www.instagram.com/')
        return "window.__additionalDataLoaded('feed'" in response.text

    def login(self, sessionid=None):
        if sessionid is None:
            sessionid = getpass('Please enter sessionid: ')
        self.session.cookies.clear()
        self.session.cookies.set(
            'sessionid',
            sessionid,
            domain='.instagram.com',
            secure=True,
            expires=int(time.time()) + 365 * 24 * 3600,
            discard=False,
            rest={'HttpOnly': True}
        )

        if not self.is_logined():
            raise Exception('Instagram login failed.')

    def reels_media(self, user_id):
        headers = {
            'Referer': 'https://www.instagram.com/',
            # x-ig-app-id为位于 https://www.instagram.com/service-worker-prod-es6.js 中的instagramWebDesktopFBAppId值
            'x-ig-app-id': '936619743392459'
        }
        response = self.session.get('https://i.instagram.com/api/v1/feed/reels_media/', params={'reel_ids': user_id},
                                    headers=headers, allow_redirects=False)
        if response.status_code != 200:
            if response.status_code == 302:
                raise Exception('reels_media failed. {} {} {} {}'.format(
                    response.status_code, response.reason, response.headers['Location'], response.text))
            else:
                raise Exception('reels_media failed. {} {} {}'.format(
                    response.status_code, response.reason, response.text))
        result = response.json()
        if result['status'] != 'ok':
            raise Exception('reels_media failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return result['reels_media'][0]

    def owner_to_timeline_media(self, user_id, first=12, after=None):
        variables = {
            'id': user_id,
            'first': first
        }
        if after is not None:
            variables['after'] = after

        headers = {
            'Referer': 'https://www.instagram.com/',
            'x-requested-with': 'XMLHttpRequest'
        }
        csrftoken = self.session.cookies.get(
            'csrftoken', domain='.instagram.com')
        if csrftoken:
            headers['x-csrftoken'] = csrftoken
        response = self.session.get('https://www.instagram.com/graphql/query/', params={
            'query_hash': '32b14723a678bd4628d70c1f877b94c9',
            'variables': json.dumps(variables, separators=(',', ':'))
        }, headers=headers, allow_redirects=False)
        if response.status_code != 200:
            if response.status_code == 302:
                raise Exception('owner_to_timeline_media failed. {} {} {} {}'.format(
                    response.status_code, response.reason, response.headers['Location'], response.text))
            else:
                raise Exception('owner_to_timeline_media failed. {} {} {}'.format(
                    response.status_code, response.reason, response.text))
        result = response.json()
        if result['status'] != 'ok':
            raise Exception('owner_to_timeline_media failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return result['data']
