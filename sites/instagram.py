from .site import Site
import json


class Instagram(Site):
    # story url: Login required GET https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}

    def owner_to_timeline_media(self, user_id, first=12, after=None):
        variables = {
            'id': user_id,
            'first': first
        }
        headers = {
            'Referer': 'https://www.instagram.com/',
            'x-requested-with': 'XMLHttpRequest'
        }
        csrftoken = self.session.cookies.get(
            'csrftoken', domain='.instagram.com')
        if csrftoken:
            headers['x-csrftoken'] = csrftoken
        if after is not None:
            variables['after'] = after
        response = self.session.get('https://www.instagram.com/graphql/query/', params={
            'query_hash': '003056d32c2554def87228bc3fd9668a',
            'variables': json.dumps(variables, separators=(',', ':'))
        }, headers=headers, allow_redirects=False)
        if response.status_code != 200:
            raise Exception('owner_to_timeline_media failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        result = response.json()
        if result['status'] != 'ok':
            raise Exception('owner_to_timeline_media failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return result['data']
