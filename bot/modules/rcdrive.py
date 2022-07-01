from configparser import ConfigParser
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from bot import LOGGER, dispatcher, USER_Drive, CONFIG_DIR
from bot.helper.telegram_helper.message_utils import editMessage, sendMarkup, auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper import button_build
from bot.helper.ext_utils.db_handler import DbManger
from html import escape
from threading import Thread
from os import path as ospath, makedirs as osmakedirs, remove as osremove, rename as osrename

FIRST, SECOND = range(2)

def rclone_buttons(update, context):
    user_id = update.message.from_user.id
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Add config", f"RCadd_{user_id}")
    buttons.sbutton("Delete config", f"RCdelete_{user_id}")
    buttons.sbutton("Switch drive", f"RCdrive_{user_id}")
    buttons.sbutton("Switch path", f"RCpath_{user_id}")
    buttons.sbutton('Quit', f"RCcancel_{user_id}")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    msg_text =""
    if not USER_Drive.get(user_id):
        msg_text = "You have not added the rclone config file yet.\nPlease add your rclone config file."
    else:
        rc_conf_path = USER_Drive.get(user_id)['rc_conf_path']
        config = ConfigParser()
        config.read(rc_conf_path)
        sections = config.sections()
        msg_text += f"Current rclone config state:\n<b>Drive: </b><code>{USER_Drive.get(user_id)['drive_letter']}</code>\n"
        msg_text += f"<b>Path: </b><code>{USER_Drive.get(user_id)['dest_dir']}</code>\n"
        msg_text += f"<b>Total: </b><code>{len(sections)}</code>\n"
    sendMarkup(msg_text, context.bot, update.message, button)
    return FIRST

def rccancel_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]) and not CustomFilters._owner_query(user_id):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    else:
        query.answer()
        LOGGER.info("Opration canceled!")
        editMessage("Opration canceled!\n", msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
        return ConversationHandler.END


def rcdelete_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    if not USER_Drive.get(user_id):
        query.answer(text="You have not added the rclone config file ", show_alert=True)
        return FIRST
    else:
        query.answer()
        msg_text = "Are you sure you want to delete the rclone config file?"
        button = button_build.ButtonMaker()
        button.sbutton("Yes", f"RCdelyes_{user_id}")
        button.sbutton("No", f"RCcancel_{user_id}")
        button = InlineKeyboardMarkup(button.build_menu(2))
        editMessage(msg_text, msg, button)
        return SECOND

def rcdelete_yes_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data = query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return SECOND
    else:
        try:
            query.answer()
            del USER_Drive[user_id]
            DbManger().drive_delete(user_id)
            msg_text = "Deleting rclone config file..."
        except Exception as e:
            LOGGER.error(e)
            msg_text = f"{e} Error deleting rclone config file!"
        editMessage(msg_text, msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
        return ConversationHandler.END


def rcdrive_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    if not USER_Drive.get(user_id):
        query.answer(text="You have not added the rclone config file ", show_alert=True)
        return FIRST
    else:
        query.answer()
        rc_conf_path = USER_Drive.get(user_id)['rc_conf_path']
        config = ConfigParser()
        config.read(rc_conf_path)
        sections = config.sections()
        buttons = button_build.ButtonMaker()
        for section in sections:
            buttons.sbutton(section, f"RCselect_{section}_{user_id}")
        buttons.sbutton("Cancel", f"RCcancel_{user_id}")
        button = InlineKeyboardMarkup(buttons.build_menu(2))
        msg_text = f"""Default section of rclone config: <b>{USER_Drive.get(user_id)['drive_letter']}</b>\nPlease choose you want to use:"""
        editMessage(msg_text, msg, button)
        return SECOND

def rcdrive_select_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[2]):
        query.answer(text="Not Yours!", show_alert=True)
        return SECOND
    else:
        query.answer()
        selection = data[1]
        USER_Drive[user_id]['drive_letter'] = selection
        DbManger().drive_letter_update(user_id, selection)
        editMessage(f"Drive letter changed to {selection}", msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
        return ConversationHandler.END


def rcpath_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    if not USER_Drive.get(user_id):
        query.answer(text="You have not added the rclone config file ", show_alert=True)
        return FIRST
    else:
        query.answer()
        dest_dir = escape(USER_Drive.get(user_id)['dest_dir'])
        msg_text = f"Default path of rclone upload: <b>{dest_dir}</b>\nPlease input the new path:"
        editMessage(msg_text, msg)
        return SECOND

def rcpath_input_callback(update, context):
    msg = update.message
    user_id = msg.from_user.id
    text = msg.text.strip()
    if not text:
        sendMessage("Path cannot be empty!", context.bot, msg)
        return SECOND
    else:
        dest_dir = ospath.join('/', text)
        USER_Drive[user_id]['dest_dir'] = text
        DbManger().drive_destdir_update(user_id, dest_dir)
        reply_message = sendMessage(f"Path changed to {escape(dest_dir)}", context.bot, msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, reply_message)).start()
        return ConversationHandler.END


def rcadd_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    else:
        query.answer()
        editMessage("Please direct send your rclone config file.", msg)
        return SECOND

def receive_config (update, context):
    msg = update.message
    user_id = msg.from_user.id
    config_file = msg.document.get_file()
    rc_conf_dir = ospath.join(CONFIG_DIR, str(user_id))
    rc_conf_path = ospath.join(rc_conf_dir, 'rclone.conf')
    if not ospath.exists(rc_conf_dir):
        osmakedirs(rc_conf_dir)
    config_file.download(rc_conf_path + '.tmp')
    try:
        config = ConfigParser()
        config.read(rc_conf_path + '.tmp')
        sections = config.sections()
        if not sections:
            sendMessage("Invalid Rclone config file!\n Please resend the config file", context.bot, msg)
            return SECOND
        else:
            if ospath.exists(rc_conf_path):
                osremove(rc_conf_path)
            osrename(rc_conf_path + '.tmp', rc_conf_path)
            drive_letter = sections[0]
            USER_Drive[user_id] = {'rc_conf_path': rc_conf_path, 'drive_letter': drive_letter, 'dest_dir': '/'}
            DbManger().drive_add(user_id, rc_conf_path, drive_letter, '/')
            reply_message = sendMessage(f"Rclone config file added successfully!\nDrive letter: {drive_letter}\nDestination directory: {escape('/')}", context.bot, msg)
            Thread(target=auto_delete_message, args=(context.bot, msg, reply_message)).start()
            return ConversationHandler.END
    except Exception as e:
        LOGGER.error(e)
        sendMessage(f'{e}\n Please resend the config file', context.bot, msg)
        return SECOND

 
conv_handler = ConversationHandler(
    entry_points=[CommandHandler(BotCommands.RcdriveCommand, rclone_buttons, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)],
    states={
        FIRST: [CallbackQueryHandler(rcdrive_callback, pattern=r'RCdrive_.*'),
                CallbackQueryHandler(rcpath_callback, pattern=r'RCpath_.*'),
                CallbackQueryHandler(rcadd_callback, pattern=r'RCadd_.*'),
                CallbackQueryHandler(rcdelete_callback, pattern=r'RCdelete_.*')],
        SECOND: [MessageHandler(Filters.document, receive_config),
                MessageHandler(Filters.text, rcpath_input_callback),
                CallbackQueryHandler(rcdrive_select_callback, pattern=r'RCselect_.*'),
                CallbackQueryHandler(rcdelete_yes_callback, pattern=r'RCdelyes_.*')],
    },
    fallbacks=[CallbackQueryHandler(rccancel_callback, pattern=r'RCcancel_.*')],
    run_async=True)
dispatcher.add_handler(conv_handler)
