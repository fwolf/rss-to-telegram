# _*_ coding: utf-8 _*_

from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from dateutil.parser import parse
from config import config
import feedparser
import telebot
import json
import os


def get_timestamp(dt):
    return parse(dt).timestamp()


# Ref: https://stackoverflow.com/a/9045719/1759745
KEEP_ATTRIBUTES = [
    'href'
]


def clean_tags(tag):
    if NavigableString == type(tag):
        return tag

    # 递归，先处理子结点，不然 unwrap 后本结点就变性了
    for child in tag.contents :
        clean_tags(child)

    if tag.name not in ['b', 'i', 'a', 'code', 'pre']:
        tag.unwrap()

    if tag.name == 'a' :
        allowed_attrs = {}
        for key in tag.attrs :
            if key in KEEP_ATTRIBUTES :
                allowed_attrs[key] = tag.attrs[key]
        tag.attrs = allowed_attrs

    return tag


bot = telebot.TeleBot(config.get('telegram-token'))

feeds = list()

if type(config.get('feeds')) == str:
    feeds.append(feedparser.parse(config.get('feeds')))
else:
    for feed in config.get('feeds'):
        feeds.append(feedparser.parse(feed))

new_posts = []

if not os.path.exists('posts.json'):
    with open('posts.json', 'w') as f:
        json.dump([], f)
        f.close()

with open('posts.json') as f:
    guids = json.load(f)
    f.close()

for feed in feeds:
    prefix = feed.feed.title + ' (' + feed.feed.authors[0].email + ')' + '\n\n'
    for entry in feed.entries:
        content = entry['description']
        content = content.replace('<br>', '\n').replace('<br />', '\n')

        post = {}
        soup = BeautifulSoup(content, 'lxml')
        if soup.img:
            post['image'] = soup.img['src']

        clean_tags(soup.html.body)

        post['text'] = prefix
        for part in soup.html.contents :
            post['text'] += str(part)
        post['text'] += '\n\n{}'.format(entry['link'])
        post['date'] = get_timestamp(entry['published'])

        if entry['guid'] not in guids:
            # TODO: strip guid with a regex like /d{4,}\/{?}$/
            new_posts.append(post)
            guids.append(entry['guid'])

new_posts.sort(key=lambda x: x['date'])

for post in new_posts:
    bot.send_message(
        config.get('channel-id'),
        post.get('text'),
        parse_mode='HTML',
        disable_web_page_preview=True
        )

with open('posts.json', 'w') as f:
    json.dump(guids, f)
    f.close()
