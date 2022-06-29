import time
from threading import Thread
from html import escape
from telegram.ext import CommandHandler
from bot import dispatcher
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

def info(update, context):
    mesg = update.message.to_dict()
    msg = f""
    mesg_from = mesg.get('from', None)
    if mesg_from:
        username = mesg_from['username'] if mesg_from.get('username') else mesg_from['last_name'] + mesg_from['first_name']
        user_id = mesg_from['id']
        lan = mesg_from['language_code']
        msg += f"<b>Name: </b><code>{escape(username)}</code>\n<b>UserID: </b>{user_id}\n<b>Language: </b>{lan}\n"
    chat = mesg.get('chat', None)
    if chat:
        chat_type = chat['type']
        msg += f'<b>Type: </b>{chat_type}\n'
        if chat_type in ['group', 'supergroup']:
            group_id = chat['id']
            msg += f'<b>GroupId: </b>{group_id}\n'
    reply_mesg = mesg.get('reply_to_message', None)
    if reply_mesg:
        forward_from = reply_mesg.get('forward_from_chat', None)
        if forward_from:
            chatid = forward_from['id']
            msg += f'<b>ChatId: </b>{chatid}\n'
        media_type = ['document', 'video', 'audio', 'photo']
        for i in media_type:
            media_type = reply_mesg.get(i)
            if media_type:
                if i == 'photo':
                    FileId = media_type[-1].get('file_unique_id')   
                else:
                    FileId = media_type.get('file_unique_id')
                msg += f'<b>FileId: </b>{FileId}\n'
                break    
    date = mesg.get('date','')
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(date))
    msg += f'<b>Date: </b>{date}'
    reply_mesg = sendMessage(msg, context.bot, update.message)
    Thread(target=auto_delete_message, args=(context.bot, update.message, reply_mesg)).start()

info_handler = CommandHandler(BotCommands.InfoCommand, info, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(info_handler)
