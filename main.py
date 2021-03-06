# _*_ coding: utf-8 _*_

from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from dateutil.parser import parse
from config import config
from pymediainfo import MediaInfo
from telebot.types import InputMediaAnimation, InputMediaPhoto, InputMediaVideo
from html import escape
import feedparser
import re
import telebot
import json
import os


def get_timestamp(dt):
    return parse(dt).timestamp()


# Ref: https://stackoverflow.com/a/9045719/1759745
KEEP_ATTRIBUTES = [
    'href'
]


def clean_tags(tag, post):
    if NavigableString == type(tag):
        tag.string.replace_with(escape(tag))
        return tag

    # 递归，先处理子结点，不然 unwrap 后本结点就变性了
    for child in tag.contents :
        clean_tags(child, post)

    if 'img' == tag.name :
        if 'src' in tag.attrs :
            post['images'].append(fix_url(tag.attrs['src']))
        if 'title' in tag.attrs :
            title = tag.attrs['title']
            tag.insert_before(NavigableString('[' + title + ']'))

    if tag.name not in ['b', 'i', 'a', 'code', 'pre']:
        tag.unwrap()

    if tag.name == 'a' :
        allowed_attrs = {}
        for key in tag.attrs :
            if key in KEEP_ATTRIBUTES :
                allowed_attrs[key] = tag.attrs[key]
        tag.attrs = allowed_attrs

    return tag


def is_video_has_sound(src):
    media_info = MediaInfo.parse(src)
    hasSound = False
    for track in media_info.tracks:
        if 'Audio' == track.track_type :
            hasSound = True

    return hasSound


# Some photo may meet size limit
# https://stackoverflow.com/a/52315151/1759745
def send_photo(bot, chat_id, url, caption):
    try :
        bot.send_photo(chat_id, url, caption=caption, parse_mode='HTML')
    except telebot.apihelper.ApiException as e:
        # Upload as document first to get cached
        bot.send_document(chat_id, url, caption='', parse_mode='HTML')
        bot.send_photo(chat_id, url, caption=caption, parse_mode='HTML')


def send_album(bot, chat_id, image_urls, video_urls):
    medias = []
    for url in image_urls :
        medias.append(InputMediaPhoto(url))
    for url in video_urls :
        medias.append(InputMediaVideo(video))
    try :
        bot.send_media_group(chat_id, medias)

    except telebot.apihelper.ApiException as e:
        for url in image_urls :
            bot.send_document(chat_id, url)
        for url in image_urls :
            bot.send_document(chat_id, url)
        bot.send_media_group(chat_id, medias)


def fix_url(url):
    if ('//' == url[0:2]) :
        url = 'http:' + url
    return url


bot = telebot.TeleBot(config.get('telegram-token'))

feeds = list()

if type(config.get('feeds')) == str:
    feeds.append(feedparser.parse(config.get('feeds')))
else:
    for feed in config.get('feeds'):
        feeds.append(feedparser.parse(feed))

if not os.path.exists('posts.json'):
    with open('posts.json', 'w') as f:
        json.dump([], f)
        f.close()

with open('posts.json') as f:
    guids = json.load(f)
    f.close()

for feed in feeds:
    if ('atom10' == feed.version) :
        prefix = feed.feed.title + ' (' + feed.feed.authors[0].email + ')' + '\n\n'
    elif ('rss20' == feed.version) :
        prefix = feed.channel.title + ' (' + feed.channel.link + ')' + '\n\n'

    for entry in feed.entries:
        content = entry['description']
        content = content.replace('<br>', '\n').replace('<br />', '\n')

        post = {}
        post['images'] = []
        post['gifs'] = []
        post['videos'] = []
        soup = BeautifulSoup(content, 'lxml')
        if soup.img:
            post['images'].append(fix_url(soup.img['src']))

        clean_tags(soup.html.body, post)

        post['text'] = prefix
        for part in soup.html.contents :
            post['text'] += str(part)
        post['text'] += '\n\n{}'.format(entry['link'])
        post['date'] = get_timestamp(entry['published'])

        if entry['guid'] in guids:
            continue

        # Find images
        # video: <link rel="enclosure" type="video/mp4" length="2365692" href="https://cmx.social/system/media_attachments/files/001/901/934/original/812bfbf669d03cec.mp4"/>
        #   gif: <link rel="enclosure" type="video/mp4" length="20395" href="https://cmx.social/system/media_attachments/files/001/901/927/original/314f914a5ac552f1.mp4"/>
        for link in entry.links :
            if 'enclosure' == link.rel :
                url = fix_url(link.href)
                if ('image' == link.type[0:5]) :
                    post['images'].append(url)
                elif ('video' == link.type[0:5]) :
                    if (is_video_has_sound(url)) :
                        post['videos'].append(url)
                    else :
                        post['gifs'].append(url)

        # Unique medias
        post['images'] = list(set(post['images']))
        post['videos'] = list(set(post['videos']))
        post['gifs'] = list(set(post['gifs']))

        # Reveme weibo face
        regex = re.compile(r'https?:\/\/\w*img\w*.\w+.sinajs.cn\/\w+\d+\/style\/images\/\w+\/face\/')
        post['images'] = [i for i in post['images'] if not regex.match(i)]

        # Send
        chat_id = config.get('channel-id')
        caption = ''
        if (1 < (len(post['images']) + len(post['videos']))) :
            bot.send_message(
                chat_id,
                post.get('text'),
                parse_mode='HTML',
                disable_web_page_preview=True
                )
            send_album(bot, chat_id, post['images'], post['videos'])

        else :
            if (1024 < len(post.get('text').encode('utf8'))) :
                bot.send_message(
                    chat_id,
                    post.get('text'),
                    parse_mode='HTML',
                    disable_web_page_preview=True
                    )
            else :
                caption = post.get('text')

                for image in post['images'] :
                    send_photo(bot, chat_id, image, caption)
                    caption = ''
                for video in post['videos'] :
                    bot.send_video(chat_id, video, caption=caption, parse_mode='HTML')
                    caption = ''

        # PR: https://github.com/eternnoir/pyTelegramBotAPI/pull/620 not approved
            for gif in post['gifs'] :
        #        bot.send_animation(chat_id, gif, caption=caption, parse_mode='HTML')
                bot.send_document(chat_id, gif, caption=caption, parse_mode='HTML')
                caption = ''


        # Save progress for each post, in case of error, will not dup send
        # TODO: strip guid with a regex like /d{4,}\/{?}$/
        guids.append(entry['guid'])
        with open('posts.json', 'w') as f:
            json.dump(guids, f)
            f.close()
