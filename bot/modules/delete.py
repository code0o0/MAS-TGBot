from threading import Thread
from telegram.ext import CommandHandler
from base64 import b64decode
from bot import dispatcher, LOGGER, HHD_DIR, USER_RcDrive
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.ext_utils.bot_utils import is_gdrive_link
from subprocess import run as srun
from os import path as ospath
from html import escape

def delete_file(update, context):
    msg = update.message
    user_id = msg.from_user.id
    mesg_args = msg.text.split('/del', 1)[-1]
    mesg_args = mesg_args.strip()
    reply_to = msg.reply_to_message
    if mesg_args:
        link = mesg_args
    elif reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ''
    if is_gdrive_link(link):
        LOGGER.info(link)
        drive = gdriveTools.GoogleDriveHelper()
        msg = drive.deletefile(link)
    elif link.startswith('RcDride:'):
        _drive, _name = link.strip('RcDride:').split('.', maxsplit=1)
        try:
            _pathname = b64decode(_name).decode('utf-8')
            if len(_pathname) > len(USER_RcDrive.get(user_id)['dest_dir']):
                srun(['rclone', 'purge', f"--config={USER_RcDrive.get(user_id)['rc_conf_path']}", f"{_drive}:{_pathname}"])
                msg = f'{escape(ospath.split(_pathname)[-1])} have been deleted'
            else:
                msg = "Root folder can not delete"
        except Exception as err:
            LOGGER.error(err)
            msg = err
        
    elif  link.startswith('HhDride:'):
        if CustomFilters._owner_query(user_id):
            msg = 'Only owner can upload Hddrive!'
        else:
            _name = link.split('HhDride:')[-1]
            try:
                _pathname = b64decode(_name).decode('utf-8')
                if len(_pathname) > len(HHD_DIR):
                    srun(['rm', '-rf', f"{_pathname}"])
                    msg = f'{escape(ospath.split(_pathname)[-1])} have been deleted'
                else:
                    msg = "Root folder can not delete"
            except Exception as err:
                LOGGER.error(err)
                msg = err
    else:
        msg = 'Send Gdrive link or drive path along with command'
    reply_message = sendMessage(msg, context.bot, update.message)
    Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()

delete_handler = CommandHandler(BotCommands.DeleteCommand, delete_file, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
dispatcher.add_handler(delete_handler)
