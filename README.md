rss-to-telegram

# RSS to Telegram reposter bot

This is a bot to repost given RSS feed to a Telegram channel.

To run it you gotta create your own bot via [BotFather](t.me/botfather) and obtain the token. Then do:
- Clone this repo
- Copy `config.example.py` to `config.py`
- Put all the data there: your token, chat id and feed link. [@getidsbot)](https://t.me/getidsbot) can help you with getting channel id.
- Install MediaInfo library from https://mediaarea.net/en/MediaInfo
- sudo pip3 install -r requirements.txt

Then run the bot, for example via cron as for it to regularly retrieve new feed items.


Channel id for private channel:

    "channel-id": "-100[NUMBER]"

   The [NUMBER] is id of your channel, some bot can get channel id WITH -100,
use it diretory. See:
https://github.com/python-telegram-bot/python-telegram-bot/issues/538#issuecomment-287231847
