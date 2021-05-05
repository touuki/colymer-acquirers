from sites import *
import os, sys
import acquirers
import pickle
import getopt

def usage(code=0):
    print("""Usage: python scan.py [OPTION]... SITE
    SITE should be one of [weibo|instagram|twitter]
    -h,--help:  show usage.
    -i:         only load parameters and doesn't run scanning; useful for python -i""")
    sys.exit(code)

if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "hi",['help'])
    inspect = False
    for op, value in opts:
        if op == "-i":
            inspect = True
        elif op in ("-h","--help"):
            usage()

    if len(args) == 0 or args[0] not in ['weibo', 'instagram', 'twitter']:
        print('Invalid args.')
        usage(1)

    site_name = args[0]
    user_ids = {
        'weibo': ['5825014417'],
        'instagram': ['39817910000'],
        'twitter': ['1279429216015011841', '911494401087569920']
    }
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    }
    proxies = {
        'http': 'http://localhost:7070',
        'https': 'http://localhost:7070',
    }
    colymer = Colymer('http://192.168.30.1:3000/api/')

    cookie_file = os.path.join(os.path.dirname(
        __file__), 'cookies/{}.cookie'.format(site_name))

    cookies = None
    if os.path.exists(cookie_file):
        with open(cookie_file, 'rb') as f:
            cookies = pickle.load(f)

    if site_name == 'weibo':
        client = Weibo(headers=headers, cookies=cookies)
        acquirer = acquirers.Weibo(colymer, client, site_name)
    elif site_name == 'instagram':
        client = Instagram(headers=headers, proxies=proxies, cookies=cookies)
        acquirer = acquirers.Instagram(colymer, client, site_name)
    elif site_name == 'twitter':
        client = Twitter(headers=headers, proxies=proxies, cookies=cookies)
        acquirer = acquirers.Twitter(colymer, client, site_name)

    if not inspect:
        try:
            if not client.is_logined():
                client.login()
            for user_id in user_ids[site_name]:
                acquirer.scan(user_id=user_id)

        finally:
            client.save_cookies(cookie_file)
