from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from bot import LOGGER, dispatcher, USER_GdDrive, CONFIG_DIR
from bot.helper.telegram_helper.message_utils import editMessage, sendMarkup, auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper import button_build
from bot.helper.ext_utils.db_handler import DbManger
from threading import Thread
from subprocess import run as srun
from os import path as ospath, remove as osremove, listdir as oslistdir

FIRST, SECOND, THIRD, FOURTH = range(4)
mesg_dict = {}


def gdrive_buttons(update, context):
    user_id = update.message.from_user.id
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Add config", f"GDadd_{user_id}")
    buttons.sbutton("Delete config", f"GDdelete_{user_id}")
    buttons.sbutton('Quit', f"GDcancel_{user_id}")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    msg_text =""
    if not USER_GdDrive.get('parent_id'):
        msg_text = "G-drive not setting!\nPlease add google drive account."
    else:
        account = oslistdir(USER_GdDrive.get('account_path'))
        msg_text += f"Current G-drive config state:\n<b>FolderID: </b><code>{USER_GdDrive.get('parent_id')}</code>\n"
        msg_text += f"<b>TeamDrive: </b><code>{USER_GdDrive.get('isteam_drive')}</code>\n"
        msg_text += f"<b>Account: </b><code>{len(account)}</code>\n"
    sendMarkup(msg_text, context.bot, update.message, button)
    return FIRST


def gdcancel_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    else:
        query.answer()
        LOGGER.info("Opration canceled!")
        editMessage("Opration canceled!\n", msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
        return ConversationHandler.END


def gddelete_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    if not USER_GdDrive.get('parent_id'):
        query.answer(text="You have not added the google deive", show_alert=True)
        return FIRST
    else:
        query.answer()
        msg_text = "Are you sure you want to delete the google deive config?"
        button = button_build.ButtonMaker()
        button.sbutton("Yes", f"GDdelyes_{user_id}")
        button.sbutton("No", f"GDcancel_{user_id}")
        button = InlineKeyboardMarkup(button.build_menu(2))
        editMessage(msg_text, msg, button)
        return SECOND

def gddelete_yes_callback(update, context):
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
            USER_GdDrive.clear()
            DbManger().gddrive_delete()
            msg_text = "Deleting google deive config..."
        except Exception as e:
            LOGGER.error(e)
            msg_text = f"{e} Error deleting google deive config!"
        editMessage(msg_text, msg)
        Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
        return ConversationHandler.END


def gdadd_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return FIRST
    if USER_GdDrive.get('parent_id'):
        query.answer(text="You have already added the google drive!", show_alert=True)
        return FIRST
    else:
        query.answer()
        editMessage("Please direct send your google drive folder id", msg)
        return SECOND

def gdadd_parent_id_callback(update, context):
    msg = update.message
    user_id = msg.from_user.id
    text = msg.text.strip()
    if not text:
        sendMessage("Folder id cannot be empty!", context.bot, msg)
        return SECOND
    else:
        mesg_dict['parent_id'] = text
        msg_text = "Is it a teamdrive?"
        button = button_build.ButtonMaker()
        button.sbutton("Yes", f"GDteamyes_{user_id}")
        button.sbutton("No", f"GDteamno_{user_id}")
        button = InlineKeyboardMarkup(button.build_menu(2))
        sendMarkup(msg_text, context.bot, msg, button)
        return THIRD


def gdadd_team_drive_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return THIRD
    else:
        query.answer()
        if query.data == f"GDteamyes_{user_id}":
            mesg_dict['isteam_drive'] = True
        elif query.data == f"GDteamno_{user_id}":
            mesg_dict['isteam_drive'] = False
        msg_text = "Are you using a google service account?"
        button = button_build.ButtonMaker()
        button.sbutton("Yes", f"GDsayes_{user_id}")
        button.sbutton("No", f"GDsano_{user_id}")
        button = InlineKeyboardMarkup(button.build_menu(2))
        editMessage(msg_text, msg, button)
        return THIRD


def gdadd_service_account_callback(update, context):
    query = update.callback_query
    msg = query.message
    user_id = query.from_user.id
    data=query.data.split('_')
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return THIRD
    else:
        query.answer()
        if query.data == f"GDsayes_{user_id}":
            mesg_dict['isservice_account'] = True
            msg_text = "Please direct send your google service zip account file"
        elif query.data == f"GDsano_{user_id}":
            mesg_dict['isservice_account'] = False
            msg_text = "Please direct send your google token.pickle file"
    editMessage(msg_text, msg)
    return FOURTH


def gdadd_receive_sa_callback(update, context):
    msg = update.message
    try:
        tg_file = msg.document.get_file()
        sa_zip_path = ospath.join(CONFIG_DIR, 'accounts.zip')
        tg_file.download(sa_zip_path)
        sa_dir = ospath.join(CONFIG_DIR, 'accounts')
        srun(["rm", "-rf", sa_dir])
        srun(["unzip", "-q", "-o", sa_zip_path, "-d", sa_dir])
        srun(["chmod", "-R", "777", sa_dir])
        osremove(f"sa_zip_path")
        mesg_dict['account_path'] = sa_dir
        mesg_dict['token_path'] = ''
        USER_GdDrive.update(mesg_dict)
        isteam_drive =1 if USER_GdDrive['isteam_drive'] else 0
        isservice_account = 1 if USER_GdDrive['isservice_account'] else 0
        DbManger.gddrive_add(parent_id=USER_GdDrive['parent_id'], isteam_drive=isteam_drive, isservice_account=isservice_account, account_path=USER_GdDrive['account_path'], token_path=USER_GdDrive['token_path'])
        mesg_dict.clear()
        msg_text = "Google service account zip file received!"
    except Exception as e:
        LOGGER.error(e)
        msg_text = f"{e} Error receiving google service account zip file, please try again!"
        editMessage(msg_text, msg)
        return FOURTH
    editMessage(msg_text, msg)
    Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
    return ConversationHandler.END
    
def gdadd_receive_token_callback(update, context):
    msg = update.message
    try:
        tg_file = msg.document.get_file()
        token_path = ospath.join(CONFIG_DIR, 'token.pickle')
        tg_file.download(token_path)
        mesg_dict['token_path'] = token_path
        mesg_dict['account_path'] = ''
        USER_GdDrive.update(mesg_dict)
        isteam_drive =1 if USER_GdDrive['isteam_drive'] else 0
        isservice_account = 1 if USER_GdDrive['isservice_account'] else 0
        DbManger.gddrive_add(parent_id=USER_GdDrive['parent_id'], isteam_drive=isteam_drive, isservice_account=isservice_account, account_path=USER_GdDrive['account_path'], token_path=USER_GdDrive['token_path'])
        mesg_dict.clear()
        msg_text = "Google token.pickle file received!"   
    except Exception as e:
        LOGGER.error(e)
        msg_text = f"{e} Error receiving google token.pickle file, please try again!"
        editMessage(msg_text, msg)
        return FOURTH
    editMessage(msg_text, msg)
    Thread(target=auto_delete_message, args=(context.bot, msg, msg.reply_to_message)).start()
    return ConversationHandler.END
    

conv_handler = ConversationHandler(
    entry_points=[CommandHandler(BotCommands.GddriveCommand, gdrive_buttons, filters=CustomFilters.owner_filter)],
    states={
        FIRST: [CallbackQueryHandler(gddelete_callback, pattern=r"GDdelete_*"),
                CallbackQueryHandler(gdadd_callback, pattern=r"GDadd_*")],
        SECOND: [CallbackQueryHandler(gddelete_yes_callback, pattern=r"GDdelyes_*"),
                MessageHandler(Filters.text, gdadd_parent_id_callback)],
        THIRD: [CallbackQueryHandler(gdadd_team_drive_callback, pattern=r"GDteam_*"),
                CallbackQueryHandler(gdadd_service_account_callback, pattern=r"GDsa*")],
        FOURTH: [MessageHandler(Filters.document.file_extension("zip"), gdadd_receive_sa_callback),
                MessageHandler(Filters.document.file_extension("pickle"), gdadd_receive_token_callback)]
        },
    fallbacks=[CallbackQueryHandler(gdcancel_callback, pattern=r"GDcancel_*")],
    run_async=True,
    conversation_timeout = 120
)
dispatcher.add_handler(conv_handler)
