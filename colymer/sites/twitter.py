from .site import Site
import json
import time
import re


class TwitterSite(Site):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._get_guest_token()
        # queryIds可考虑从 https://abs.twimg.com/responsive-web/client-web/main.79e382f5.js 动态获取
        self.queryIds = {
            'UserByRestIdWithoutResults': 'WN6Hck-Pwm-YP0uxVj1oMQ',
            'UserTweets': 'VFKEUw-6LUwwZtrnSuX_PA',
            'UserTweetsAndReplies': 'moGqlVrYb60N3gzx3iTIpA',
        }

    def _get_guest_token(self):
        self.session.cookies.clear_expired_cookies()
        guest_token = self.session.cookies.get(
            'gt', domain='.twitter.com')
        if guest_token:
            return guest_token
        else:
            response = self.session.get('https://twitter.com/', timeout=self.timeout)
            searchObj = re.search(
                r'document\.cookie="gt=(\d+); Max-Age=(\d+); Domain=\.twitter\.com; Path=/; Secure"',
                response.text
            )
            if searchObj:
                self.session.cookies.set(
                    'gt',
                    searchObj.group(1),
                    domain='.twitter.com',
                    secure=True,
                    expires=int(time.time()) + int(searchObj.group(2)),
                    discard=False
                )
                return searchObj.group(1)
            else:
                raise Exception('Can not obtain guest token.')

    def _get_api_headers(self):
        headers = {
            'Referer': 'https://twitter.com/',
            'content-type': 'application/json',
            # authorization为 https://abs.twimg.com/responsive-web/client-web/main.79e382f5.js 中的固定值，可考虑从user主页中动态获取
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-twitter-active-user': 'yes',
            'x-guest-token': self._get_guest_token()
        }
        '''
        csrf_token = self.session.cookies.get(
            'ct0', domain='.twitter.com')
        if csrf_token:
            headers['x-csrf-token'] = csrf_token
        '''
        return headers

    def _postprocess_response(self, response, method_name):
        if response.status_code != 200:
            if response.status_code == 302:
                raise Exception('{} failed. {} {} {} {}'.format(
                    method_name, response.status_code, response.reason, response.headers['Location'], response.text))
            else:
                raise Exception('{} failed. {} {} {}'.format(
                    method_name, response.status_code, response.reason, response.text))
        return response.json()

    @Site.request_wrapper
    def user_by_rest_id_without_results(self, user_id):
        """通过 https://twitter.com/i/user/:user_id 页面可发现该请求"""
        variables = {
            "userId": user_id,
            "withHighlightedLabel": True
        }

        response = self.session.get(
            'https://twitter.com/i/api/graphql/{}/UserByRestIdWithoutResults'.format(
                self.queryIds['UserByRestIdWithoutResults']),
            params={
                'variables': json.dumps(variables, separators=(',', ':'))
            },
            headers=self._get_api_headers(),
            timeout=self.timeout,
            allow_redirects=False
        )
        return self._postprocess_response(response, 'user_by_rest_id_without_results')

    @Site.request_wrapper
    def user_tweets(self, user_id, count=20, cursor=None):
        variables = {
            "userId": user_id,
            "count": count,
            "withHighlightedLabel": True,
            "withTweetQuoteCount": True,
            "includePromotedContent": True,
            "withTweetResult": False,
            "withUserResults": False,
            "withVoice": False,
            "withNonLegacyCard": True,
            "withBirdwatchPivots": False
        }
        if cursor is not None:
            variables['cursor'] = cursor

        response = self.session.get(
            'https://twitter.com/i/api/graphql/{}/UserTweets'.format(
                self.queryIds['UserTweets']),
            params={
                'variables': json.dumps(variables, separators=(',', ':'))
            },
            headers=self._get_api_headers(),
            timeout=self.timeout,
            allow_redirects=False
        )
        return self._postprocess_response(response, 'user_tweets')

    @Site.request_wrapper
    def user_tweets_and_replies(self, user_id, count=20, cursor=None):
        variables = {
            "userId": user_id,
            "count": count,
            "withHighlightedLabel": True,
            "withTweetQuoteCount": True,
            "includePromotedContent": True,
            "withTweetResult": False,
            "withUserResults": False,
            "withVoice": False,
            "withNonLegacyCard": True,
            "withBirdwatchPivots": False
        }
        if cursor is not None:
            variables['cursor'] = cursor

        response = self.session.get(
            'https://twitter.com/i/api/graphql/{}/UserTweetsAndReplies'.format(
                self.queryIds['UserTweetsAndReplies']),
            params={
                'variables': json.dumps(variables, separators=(',', ':'))
            },
            headers=self._get_api_headers(),
            timeout=self.timeout,
            allow_redirects=False
        )
        return self._postprocess_response(response, 'user_tweets_and_replies')
