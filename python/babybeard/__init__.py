from telepot import glance, message_identifier
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from skybeard.beards import BeardChatHandler, ThatsNotMineException
from skybeard.decorators import onerror
from skybeard.utils import get_args


class Babybeard(BeardChatHandler):

    __userhelp__ = """As requested, a reminder for feeding the baby"""

    __commands__ = [
        # command, callback coro, help text
        ("startbabyfeed", 'start',
         'Use the first time the baby is fed to start the reminders')
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.router.routing_table['_bfeed'] = self.on__remind

    @onerror
    async def new_reminder(self, msg):
        event = self.scheduler.make_event_data('_chat', dict(name_msg=msg))
        time = 2.5 * 60 * 60  # put in a config in future
        self.scheduler.event_later(time, ('_bfeed', event))

    @onerror
    async def start(self, msg):
        await self.send_keyboard(msg)

    @onerror
    async def on__remind(self, data):
        await self.send_keyboard(data)

    @onerror
    async def send_keyboard(self, msg_or_data):
        try:
            d = msg_or_data['_bfeed']['_chat']['name_msg']
            user = d['from']['id']
        except KeyError:
            user = msg_or_data['from']['id']

        inline_keyboard = [[
                InlineKeyboardButton(
                    text = 'Click here when you have fed the baby',
                    callback_data = self.serialize(user))]]
        await self.sender.sendMessage(
                text = '*FEEDING TIME!*',
                parse_mode = 'markdown',
                reply_markup = InlineKeyboardMarkup(inline_keyboard = inline_keyboard))

    @onerror
    async def on_callback_query(self, msg):
        query_id, from_id, query_data = glance(msg, flavor='callback_query')
        try:
            data = self.deserialize(query_data)
        except ThatsNotMineException:
            return

        if data == msg['from']['id']:
            await self.new_reminder(msg)

        await self.sender.sendMessage(
                "Noted! Will send the next reminder in 2.5 hours")
