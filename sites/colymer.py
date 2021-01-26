from .site import Site
import json
import urllib.parse


class Colymer(Site):
    def __init__(self, api_prefix, **kw):
        super().__init__(**kw)
        self.api_prefix = api_prefix

    def get_articles(self, collection, pipeline, collation=None):
        params = {'pipeline': json.dumps(pipeline, separators=(',', ':'))}
        if collation is not None:
            params['collation'] = json.dumps(collation, separators=(',', ':'))
        response = self.session.get(urllib.parse.urljoin(
            self.api_prefix, 'article/{}'.format(collection)), params=params)
        if not response.ok:
            raise Exception('GET articles failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return response.json()

    def post_article(self, collection, article, resolve_attachments=False, replace=False):
        response = self.session.post(urllib.parse.urljoin(self.api_prefix, 'article/{}'.format(collection)),
                                     params={'resolve_attachments': resolve_attachments, 'replace': replace}, json=article)
        if not response.ok:
            raise Exception('POST article failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return response.json()['_id']

    def get_article(self, collection, _id, projection=None):
        params = {}
        if projection is not None:
            params['projection'] = json.dumps(
                projection, separators=(',', ':'))
        response = self.session.get(urllib.parse.urljoin(
            self.api_prefix, 'article/{}/{}'.format(collection, _id)), params=params)
        if not response.ok:
            raise Exception('GET article failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
        return response.json()

    def put_article(self, collection, _id, update):
        response = self.session.put(urllib.parse.urljoin(self.api_prefix, 'article/{}/{}'.format(
            collection, _id)), json=update)
        if not response.ok:
            raise Exception('GET article failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))

    def delete_article(self, collection, _id):
        response = self.session.delete(urllib.parse.urljoin(
            self.api_prefix, 'article/{}/{}'.format(collection, _id)))
        if not response.ok:
            raise Exception('GET article failed. {} {} {}'.format(
                response.status_code, response.reason, response.text))
