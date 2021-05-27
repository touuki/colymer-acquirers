from sites import *
import os
import sys
import acquirers
import pickle
import getopt
import traceback
import socket
import smtplib
from email.mime.text import MIMEText

tasks = {
    'weibo': [
        {'user_id': '5825014417'},
        {'user_id': '1162649274', 'q': '長濱ねる'}
    ],
    'instagram': [
        {'user_id': '39817910000'}
    ],
    'twitter': [
        {'user_id': '1279429216015011841'},
        {'user_id': '911494401087569920'},
        {'user_id': '1363706229416022021'}
    ]
}
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}
proxies = {
    'http': 'http://localhost:7070',
    'https': 'http://localhost:7070',
}
colymer = Colymer('http://192.168.30.1:3000/api/')

alert = {
    'host': '',
    'sender': '',
    'password': '',
    'receiver': ''
}


def send_error_mail(error: Exception):
    smtpObj = smtplib.SMTP_SSL(alert['host'])
    ip = smtpObj.sock.getsockname()[0]
    message = MIMEText('Hostname:{}\nIp:{}\nException:\n{}'.format(
        socket.gethostname(), ip, traceback.format_exc()))
    message['Subject'] = 'Exception occurs on {}: [{}] {}'.format(
        ip, error.__class__.__name__, error)
    message['From'] = 'Alert <{}>'.format(alert['sender'])
    message['To'] = alert['receiver']

    smtpObj.login(alert['sender'], alert['password'])
    smtpObj.sendmail(alert['sender'], [alert['receiver']], message.as_string())


def usage(code=0):
    print("""Usage: python scan.py [OPTION]... SITE
    SITE should be one of [weibo|instagram|twitter]
    -h,--help:  show usage.
    -i:         only load parameters and doesn't run scanning; useful for python -i
    -a:         used for automatically run.
                if login required, do not wait for input but raise an exception.
                if an exception is raised, send an email for alarm.""")
    sys.exit(code)


if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "hia", ['help'])
    inspect = False
    auto = False
    for op, value in opts:
        if op == "-i":
            inspect = True
        elif op == "-a":
            auto = True
        elif op in ("-h", "--help"):
            usage()

    if len(args) == 0 or args[0] not in ['weibo', 'instagram', 'twitter']:
        print('Invalid args.')
        usage(1)

    site_name = args[0]

    cookie_file = os.path.join(os.path.dirname(
        __file__), 'cookies/{}.cookie'.format(site_name))

    cookies = None
    if os.path.exists(cookie_file):
        with open(cookie_file, 'rb') as f:
            cookies = pickle.load(f)

    if site_name == 'weibo':
        client = Weibo(headers=headers, cookies=cookies, request_interval=2)
        acquirer = acquirers.Weibo(colymer, client, site_name)
    elif site_name == 'instagram':
        client = Instagram(headers=headers, proxies=proxies,
                           cookies=cookies, request_interval=15)
        if len(args) > 1 and args[1] == 'story':
            acquirer = acquirers.InstagramStory(
                colymer, client, '{}_story'.format(site_name))
        else:
            acquirer = acquirers.Instagram(colymer, client, site_name)
    elif site_name == 'twitter':
        client = Twitter(headers=headers, proxies=proxies,
                         cookies=cookies, request_interval=15)
        acquirer = acquirers.Twitter(colymer, client, site_name)

    if not inspect:
        try:
            if not client.is_logined():
                if auto:
                    raise Exception('Login required')
                else:
                    client.login()
            for kwargs in tasks[site_name]:
                acquirer.scan(**kwargs)
        except Exception as e:
            traceback.print_exc()
            if auto:
                send_error_mail(e)
        finally:
            client.save_cookies(cookie_file)
