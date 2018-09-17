from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import scoped_session, sessionmaker
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import asyncio
import logging
import os

from messages import MESSAGES
from conf import LOG_FILENAME, TOKEN, DB_FILENAME, PROXY_AUTH, PROXY_URL, MY_ID
from db_map import Users, Chats, Karma

from functions import *

logging.basicConfig(format=u'%(filename)+13s [ LINE:%(lineno)-4s] %(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.INFO, filename=LOG_FILENAME)
loop = asyncio.get_event_loop()
bot = Bot(TOKEN, parse_mode=types.ParseMode.MARKDOWN, proxy=PROXY_URL,
          proxy_auth=PROXY_AUTH)
dp = Dispatcher(bot, loop=loop, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

engine = create_engine("sqlite:///" + DB_FILENAME)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

limit_inline_btn = 5


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    me = await dp.bot.me
    if message.from_user.id == MY_ID:
        await message.reply(MESSAGES['super_admin_commands'].format(username=me.username), reply=False, parse_mode=types.ParseMode.HTML)
    elif Session.query(Users).filter(and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        await message.reply(MESSAGES['admin_commands'].format(username=me.username), reply=False, parse_mode=types.ParseMode.HTML)
    else:
        await message.reply(MESSAGES['help'], reply=False)


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply(MESSAGES['start'], reply=False)


@dp.message_handler(commands=['me'])
async def process_start_command(message: types.Message):
    chat_text = ''
    for user in Session.query(Karma).filter(Karma.user_id == message.from_user.id).all():
        current_chat = Session.query(Chats).filter(Chats.chat_id == user.chat_id).one()
        chat_text = chat_text + MESSAGES['user_karma'].format(name=current_chat.name, karma=str(user.karma))
    await bot.send_message(message.from_user.id, MESSAGES['chat_list'].format(text=chat_text),
                           disable_web_page_preview=True)

@dp.message_handler(commands=['admin'])
async def process_admin_command(message: types.Message):
    me = await dp.bot.me
    if (message.chat.type == 'group' or message.chat.type == 'supergroup') and Session.query(Users).filter(
            and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        if message.reply_to_message:
            if message.reply_to_message.from_user.id == me.id:
                await message.reply(MESSAGES['admin_not_me'], reply=False)
            elif message.reply_to_message.from_user.id == MY_ID:
                await message.reply(MESSAGES['admin_not_admin'], reply=False)
            else:
                user = Session.query(Users).filter(Users.user_id == message.reply_to_message.from_user.id).one()
                user.status = 1
                Session.commit()
                await message.reply(MESSAGES['new_admin'].format(name=prettyUsername(user.name, user.username)),
                                    reply=False)


@dp.message_handler(commands=['admins'])
async def process_admin_list_command(message: types.Message):
    if message.from_user.id == MY_ID:
        text = ''
        for admin in Session.query(Users).filter(Users.status == 1).all():
            text = text + prettyUsername(admin.name, admin.username) + '\n'
        await message.reply(MESSAGES['admin_list'].format(text=text), reply=False, disable_web_page_preview=True)


@dp.message_handler(commands=['users'])
async def process_user_list_command(message: types.Message):
    if message.from_user.id == MY_ID:
        text = ''
        for chat in Session.query(Chats).all():
            chat_text = ''
            for user in Session.query(Karma).filter(Karma.chat_id == chat.chat_id).all():
                current_user = Session.query(Users).filter(Users.user_id == user.user_id).one()
                chat_text = chat_text + MESSAGES['user_karma'].format(name=prettyUsername(current_user.name,
                            current_user.username), karma=str(user.karma))
            text = text + MESSAGES['user_chat_list'].format(text=chat_text, name=chat.name)
        await message.reply(MESSAGES['user_list'].format(text=text), reply=False, disable_web_page_preview=True)


@dp.message_handler(commands=['admin_delete'])
async def process_delete_admin_command(message: types.Message):
    me = await dp.bot.me
    if (message.chat.type == 'group' or message.chat.type == 'supergroup') and Session.query(Users).filter(
            and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        if message.reply_to_message:
            if message.reply_to_message.from_user.id == me.id:
                await message.reply(MESSAGES['admin_not_me'], reply=False)
            elif message.reply_to_message.from_user.id == MY_ID:
                await message.reply(MESSAGES['admin_not_admin'], reply=False)
            else:
                user = Session.query(Users).filter(Users.user_id == message.reply_to_message.from_user.id).one()
                user.status = 0
                Session.commit()
                await message.reply(MESSAGES['delete_admin'].format(name=prettyUsername(user.name, user.username)),
                                    reply=False)


@dp.message_handler(commands=['add'])
async def process_like_command(message: types.Message):
    me = await dp.bot.me
    if (message.chat.type == 'group' or message.chat.type == 'supergroup') and Session.query(Users).filter(
            and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        if message.reply_to_message and not message.reply_to_message.from_user.id == me.id:
            user = message.reply_to_message.from_user
            chat = message.chat
            if not Session.query(Users).filter(Users.user_id == message.from_user.id).all():
                user = Users(user_id=user.id, name=user.full_name, username=user.username)
                Session.add(user)
            if not Session.query(Karma).filter(and_((Karma.user_id == user.id), (Karma.chat_id == chat.id))).all():
                karma = Karma(user_id=user.id, chat_id=chat.id)
                Session.add(karma)
            Session.commit()



@dp.message_handler(commands=['like'])
async def process_like_command(message: types.Message):
    me = await dp.bot.me
    if (message.chat.type == 'group' or message.chat.type == 'supergroup') and Session.query(Users).filter(
            and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        if message.reply_to_message and not message.reply_to_message.from_user.id == me.id:
            user = message.reply_to_message.from_user
            chat = message.chat
            if not Session.query(Users).filter(Users.user_id == message.from_user.id).all():
                user = Users(user_id=user.id, name=user.full_name, username=user.username)
                Session.add(user)
            if not Session.query(Karma).filter(and_((Karma.user_id == user.id), (Karma.chat_id == chat.id))).all():
                karma = Karma(user_id=user.id, chat_id=chat.id)
                Session.add(karma)
            karma = Session.query(Karma).filter(and_((Karma.user_id == message.reply_to_message.from_user.id),
                                                     (Karma.chat_id == message.chat.id))).one()
            if karma:
                karma.karma += 1
                await message.reply(MESSAGES['like'].format(name=prettyUsername(
                    n=message.reply_to_message.from_user.full_name, un=message.reply_to_message.from_user.username)),
                    reply=False, disable_web_page_preview=True)
            Session.commit()
        elif not message.reply_to_message:
            users = Session.query(Karma).filter(Karma.chat_id == message.chat.id).order_by(Karma.id) \
                .limit(limit_inline_btn).all()
            inline_kb = InlineKeyboardMarkup(row_width=1)
            count = Session.query(Karma).filter(Karma.chat_id == message.chat.id).count()
            for user in users:
                current_user = Session.query(Users).filter(Users.user_id == user.user_id).one()
                inline_btn = InlineKeyboardButton(current_user.name, callback_data='like-' +
                                                                                   str(round(current_user.user_id)))
                inline_kb.add(inline_btn)
            if count > limit_inline_btn:
                inline_btn_1 = InlineKeyboardButton(' ', callback_data='none')
                inline_btn_2 = InlineKeyboardButton(' ', callback_data='none')
                inline_btn_3 = InlineKeyboardButton('>', callback_data='next-' + str(round(user.id)))
                inline_kb.row(inline_btn_1, inline_btn_2, inline_btn_3)
            await message.reply(MESSAGES['like_keyboard'], reply=False, disable_web_page_preview=True,
                                reply_markup=inline_kb)


@dp.message_handler(commands=['dislike'])
async def process_like_command(message: types.Message):
    me = await dp.bot.me
    if (message.chat.type == 'group' or message.chat.type == 'supergroup') and Session.query(Users).filter(
            and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        if message.reply_to_message and not message.reply_to_message.from_user.id == me.id:
            user = message.reply_to_message.from_user
            chat = message.chat
            if not Session.query(Users).filter(Users.user_id == message.from_user.id).all():
                user = Users(user_id=user.id, name=user.full_name, username=user.username)
                Session.add(user)
            if not Session.query(Karma).filter(and_((Karma.user_id == user.id), (Karma.chat_id == chat.id))).all():
                karma = Karma(user_id=user.id, chat_id=chat.id)
                Session.add(karma)
            karma = Session.query(Karma).filter(and_((Karma.user_id == message.reply_to_message.from_user.id),
                                                     (Karma.chat_id == message.chat.id))).one()
            if karma:
                karma.karma -= 1
                await message.reply(MESSAGES['dislike'].format(name=prettyUsername(
                    n=message.reply_to_message.from_user.full_name, un=message.reply_to_message.from_user.username)),
                    reply=False, disable_web_page_preview=True)
            Session.commit()
        elif not message.reply_to_message:
            users = Session.query(Karma).filter(Karma.chat_id == message.chat.id).order_by(Karma.id) \
                .limit(limit_inline_btn).all()
            inline_kb = InlineKeyboardMarkup(row_width=1)
            count = Session.query(Karma).filter(Karma.chat_id == message.chat.id).count()
            for user in users:
                current_user = Session.query(Users).filter(Users.user_id == user.user_id).one()
                inline_btn = InlineKeyboardButton(current_user.name, callback_data='dislike-' +
                                                                                   str(round(current_user.user_id)))
                inline_kb.add(inline_btn)
            if count > limit_inline_btn:
                inline_btn_1 = InlineKeyboardButton(' ', callback_data='none')
                inline_btn_2 = InlineKeyboardButton(' ', callback_data='none')
                inline_btn_3 = InlineKeyboardButton('>', callback_data='next-' + str(round(user.id)))
                inline_kb.row(inline_btn_1, inline_btn_2, inline_btn_3)
            await message.reply(MESSAGES['dislike_keyboard'], reply=False, disable_web_page_preview=True,
                                reply_markup=inline_kb)


@dp.message_handler(commands=['karma'])
async def process_like_command(message: types.Message):
    if Session.query(Users).filter(and_(Users.user_id == message.from_user.id, Users.status == 1)).all():
        text = ''
        for karma in Session.query(Karma).filter(Karma.chat_id == message.chat.id).order_by(Karma.karma.desc()).all():
            user = Session.query(Users).filter(Users.user_id == karma.user_id).one()
            text = text + MESSAGES['user_karma'].format(name=prettyUsername(user.name, user.username),
                                                        karma=str(karma.karma))
        await message.reply(MESSAGES['karma'].format(name=message.chat.title, text=text),
                            reply=False, disable_web_page_preview=True)


@dp.callback_query_handler(func=lambda c: c.data and c.data.startswith('like-'))
async def process_callback_like(callback_query: types.CallbackQuery):
    code = callback_query.data[5:]
    if Session.query(Users).filter(and_(Users.user_id == callback_query.from_user.id, Users.status == 1)).all():
        if Session.query(Karma).filter(and_((Karma.user_id == code),
                                            (Karma.chat_id == callback_query.message.chat.id))).all():
            karma = Session.query(Karma).filter(and_((Karma.user_id == code),
                                                     (Karma.chat_id == callback_query.message.chat.id))).one()
            karma.karma += 1
            Session.commit()
            user = Session.query(Users).filter(Users.user_id == karma.user_id).one()
            await bot.edit_message_text(MESSAGES['like'].format(name=prettyUsername(
                n=user.name, un=user.username)), callback_query.message.chat.id,
                callback_query.message.message_id, disable_web_page_preview=True)
        else:
            await bot.edit_message_text(MESSAGES['error'], callback_query.message.chat.id,
                                        callback_query.message.message_id)
    else:
        await bot.answer_callback_query(callback_query.id, MESSAGES['only_admin'])


@dp.callback_query_handler(func=lambda c: c.data and c.data.startswith('dislike-'))
async def process_callback_dislike(callback_query: types.CallbackQuery):
    code = callback_query.data[8:]
    if Session.query(Users).filter(and_(Users.user_id == callback_query.from_user.id, Users.status == 1)).all():
        if Session.query(Karma).filter(and_((Karma.user_id == code),
                                            (Karma.chat_id == callback_query.message.chat.id))).all():
            karma = Session.query(Karma).filter(and_((Karma.user_id == code),
                                                     (Karma.chat_id == callback_query.message.chat.id))).one()
            karma.karma -= 1
            Session.commit()
            user = Session.query(Users).filter(Users.user_id == karma.user_id).one()
            await bot.edit_message_text(MESSAGES['dislike'].format(name=prettyUsername(
                n=user.name, un=user.username)), callback_query.message.chat.id,
                callback_query.message.message_id, disable_web_page_preview=True)
        else:
            await bot.edit_message_text(MESSAGES['error'], callback_query.message.chat.id,
                                        callback_query.message.message_id)
    else:
        await bot.answer_callback_query(callback_query.id, MESSAGES['only_admin'])


@dp.callback_query_handler(func=lambda c: c.data and c.data.startswith('next-'))
async def process_callback_next(callback_query: types.CallbackQuery):
    code = callback_query.data[5:]
    users = Session.query(Karma).filter(and_((Karma.chat_id == callback_query.message.chat.id),
                                             (Karma.id > code))).order_by(Karma.id).limit(limit_inline_btn).all()
    count = Session.query(Karma).filter(and_((Karma.chat_id == callback_query.message.chat.id),
                                             (Karma.id <= code))).count()
    inline_kb = InlineKeyboardMarkup(row_width=1)
    for user in users:
        current_user = Session.query(Users).filter(Users.user_id == user.user_id).one()
        inline_btn = InlineKeyboardButton(current_user.name, callback_data='dislike-' +
                                                                           str(round(current_user.user_id)))
        inline_kb.add(inline_btn)
        inline_btn_1 = InlineKeyboardButton('<', callback_data='prev-' + str(code))
        inline_btn_2 = InlineKeyboardButton(' ', callback_data='none')
        if count > limit_inline_btn:
            inline_btn_3 = InlineKeyboardButton('>', callback_data='next-' + str(round(user.id)))
        else:
            inline_btn_3 = InlineKeyboardButton(' ', callback_data='none')
        inline_kb.row(inline_btn_1, inline_btn_2, inline_btn_3)
    await bot.edit_message_reply_markup(callback_query.message.chat.id, callback_query.message.message_id,
                                        reply_markup=inline_kb)


@dp.callback_query_handler(func=lambda c: c.data and c.data.startswith('prev-'))
async def process_callback_prev(callback_query: types.CallbackQuery):
    code = callback_query.data[5:]
    users = Session.query(Karma).filter(and_((Karma.chat_id == callback_query.message.chat.id),
                                             (Karma.id <= code))).order_by(Karma.id).limit(limit_inline_btn).all()
    count = Session.query(Karma).filter(and_((Karma.chat_id == callback_query.message.chat.id),
                                             (Karma.id <= code))).count()
    inline_kb = InlineKeyboardMarkup(row_width=1)
    for user in users:
        current_user = Session.query(Users).filter(Users.user_id == user.user_id).one()
        inline_btn = InlineKeyboardButton(current_user.name, callback_data='dislike-' +
                                                                           str(round(current_user.user_id)))
        inline_kb.add(inline_btn)
        if count > limit_inline_btn:
            inline_btn_1 = InlineKeyboardButton('<', callback_data='prev-' + str(round(user.id)))
        else:
            inline_btn_1 = InlineKeyboardButton(' ', callback_data='none')
        inline_btn_2 = InlineKeyboardButton(' ', callback_data='none')
        inline_btn_3 = InlineKeyboardButton('>', callback_data='next-' + str(code))
        inline_kb.row(inline_btn_1, inline_btn_2, inline_btn_3)
    await bot.edit_message_reply_markup(callback_query.message.chat.id, callback_query.message.message_id,
                                        reply_markup=inline_kb)


@dp.callback_query_handler(func=lambda c: c.data and c.data.startswith('none'))
async def process_callback_none(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, '')


@dp.message_handler(content_types=ContentType.NEW_CHAT_MEMBERS)
async def process_autoleave_new_members(message: types.Message):
    me = await dp.bot.me
    ids_new_members = []
    for member in message.new_chat_members:
        ids_new_members.append(member.id)
    if me.id in ids_new_members:
        if Session.query(Users).filter(and_(Users.user_id == message.from_user.id), (Users.status == 1)).all() and \
                (message.chat.type == 'group' or message.chat.type == 'supergroup'):
            Session.query(Chats).filter(Chats.chat_id == message.chat.id).delete()
            chat = Chats(name=message.chat.title, chat_id=message.chat.id)
            Session.add(chat)
            Session.commit()
            count = await bot.get_chat_members_count(message.chat.id)
            await bot.send_message(message.chat.id, MESSAGES['new_chat'].format(name=message.chat.title,
                                                                                count=str(count)))
        else:
            await bot.leave_chat(message.chat.id)


@dp.message_handler(content_types=ContentType.GROUP_CHAT_CREATED)
async def process_autoleave_new_chat(message: types.Message):
    if Session.query(Users).filter(and_(Users.user_id == message.from_user.id), (Users.status == 1)).all():
        chat = Chats(name=message.chat.title, chat_id=message.chat.id)
        Session.add(chat)
        Session.commit()
        count = await bot.get_chat_members_count(message.chat.id)
        await bot.send_message(message.chat.id, MESSAGES['new_chat'].format(name=message.chat.title,
                                                                            count=str(count)))
    else:
        await bot.leave_chat(message.chat.id)


@dp.message_handler(content_types=ContentType.LEFT_CHAT_MEMBER)
async def process_kick_member(message: types.Message):
    user = message.left_chat_member
    chat = message.chat
    me = await dp.bot.me
    if not message.left_chat_member.id == me.id:
        if Session.query(Users).filter(Users.user_id == user.id).all():
            Session.query(Users).filter(Users.user_id == user.id).delete()
            Session.commit()
        if Session.query(Karma).filter(and_((Karma.user_id == user.id), (Karma.chat_id == chat.id))).all():
            Session.query(Users).filter(Users.user_id == user.id).delete()
            Session.commit()
        await bot.send_message(chat.id, MESSAGES['bye'].format(name=prettyUsername(user.full_name, user.username)),
                               disable_web_page_preview=True)


if __name__ == '__main__':
    executor.start_polling(dp, on_shutdown=shutdown)
