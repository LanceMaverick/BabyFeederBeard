import datetime

from telepot import glance, message_identifier
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from skybeard.beards import BeardChatHandler, ThatsNotMineException
from skybeard.decorators import onerror
from skybeard.bearddbtable import BeardInstanceDBTable


class Babybeard(BeardChatHandler):

    __userhelp__ = """As requested, a reminder for feeding the baby"""

    __commands__ = [
        ("startbabyfeed", 'start',
         'Use the first time the baby is fed to start the reminders'),
        ("changenappy", "change_nappy", "Register a change of nappy"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.router.routing_table['_bfeed'] = self.on__remind
        self.table = BeardInstanceDBTable(self, 'dirty_nappies')

    @onerror
    async def change_nappy(self, msg):
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text='💩',
                    callback_data=self.serialize('💩')),
                InlineKeyboardButton(
                    text='💧',
                    callback_data=self.serialize('💧')),
                InlineKeyboardButton(
                    text='💩💧',
                    callback_data=self.serialize('💩💧')),
            ]],
            one_time_keyboard=True)
        await self.sender.sendMessage("What kind was it?",
                                      reply_markup=inline_keyboard)

    @onerror
    async def new_reminder(self, msg):
        event = self.scheduler.make_event_data('_chat', dict(name_msg=msg))
        # TODO put in a config in future
        time = 2.5 * 60 * 60
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
                text='Click here when you have fed the baby',
                callback_data=self.serialize('🍼'))]]
        await self.sender.sendMessage(
            text='*FEEDING TIME!*',
            parse_mode='markdown',
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=inline_keyboard))

    async def remove_keyboard(self, msg):
        return await self.bot.editMessageReplyMarkup(
            message_identifier(msg['message']),
        )

    async def update_nappy_table(self, msg):
        query_id, from_id, query_data = glance(msg, flavor='callback_query')
        try:
            data = self.deserialize(query_data)
        except ThatsNotMineException:
            return

        if data == '💩':
            with self.table as table:
                table.insert(
                    dict(timestamp=datetime.datetime.now(), dirty=True, wet=False))
        elif data == '💧':
            with self.table as table:
                table.insert(
                    dict(timestamp=datetime.datetime.now(), dirty=False, wet=True))
        elif data == '💩💧':
            with self.table as table:
                table.insert(
                    dict(timestamp=datetime.datetime.now(), dirty=True, wet=True))

        await self.remove_keyboard(msg)
        await self.bot.editMessageText(
            message_identifier(msg['message']),
            text=msg['message']['text']+": "+data,
        )
        await self.bot.answerCallbackQuery(query_id,
                                           text="Registered: "+data+" nappy.")

    @onerror
    async def on_callback_query(self, msg):
        query_id, from_id, query_data = glance(msg, flavor='callback_query')
        try:
            data = self.deserialize(query_data)
        except ThatsNotMineException:
            return

        if data == '🍼':
            await self.new_reminder(msg)
            await self.sender.sendMessage(
                "Noted! Will send the next reminder in 2.5 hours")

        if '💩' in data or '💧' in data:
            await self.update_nappy_table(msg)
