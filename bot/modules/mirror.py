from base64 import b64encode
from random import randint
from requests import utils as rutils, get as rget
from re import match as re_match, search as re_search, split as re_split
from time import sleep, time
from os import path as ospath, remove as osremove, listdir, walk
from shutil import rmtree, copyfile
from threading import Thread
from subprocess import Popen
from html import escape
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardMarkup

from bot import Interval, INDEX_URL, VIEW_LINK, aria2, QB_SEED, dispatcher, DOWNLOAD_DIR, \
    download_dict, download_dict_lock, TG_SPLIT_SIZE, LOGGER, DB_URI, INCOMPLETE_TASK_NOTIFIER, \
    EXTENSION_FILTER, HHD_DIR, USER_RcDrive, USER_GdDrive
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_mega_link, is_gdrive_link, get_content_type, get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, split_file, clean_download, get_mime_type
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException, NotSupportedExtractionArchive
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import QbDownloader
from bot.helper.mirror_utils.download_utils.mega_downloader import add_mega_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.status_utils.rc_upload_status import RcUploadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.mirror_utils.upload_utils.rc_uploader import RcUploader
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, delete_all_messages, update_all_messages, editMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper import button_build

listener_dict={}


class MirrorListener:
    def __init__(self, bot, message, isZip=False, extract=False, isQbit=False, uptype='hddrive', pswd=None, tag=None, seed=False):
        self.bot = bot
        self.message = message
        self.uid = self.message.message_id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.uptype = uptype
        self.pswd = pswd
        self.tag = tag
        self.seed = any([seed, QB_SEED])
        self.isPrivate = self.message.chat.type in ['private', 'group']

    def clean(self):
        try:
            Interval[0].cancel()
            Interval.clear()
            aria2.purge()
            delete_all_messages()
        except:
            pass

    def onDownloadStart(self):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    def onDownloadComplete(self):
        with download_dict_lock:
            LOGGER.info(f"Download completed: {download_dict[self.uid].name()}")
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
            if name == "None" or self.isQbit or not ospath.exists(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
                name = listdir(f'{DOWNLOAD_DIR}{self.uid}')[-1]
            m_path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
        size = get_path_size(m_path)
        if self.isZip:
            path = m_path + ".zip"
            with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            if self.pswd is not None:
                if self.uptype =='tgdrive' and int(size) > TG_SPLIT_SIZE:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                    self.arch_proc = Popen(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
                
                else:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                    self.arch_proc = Popen(["7z", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
            elif self.uptype =='tgdrive' and int(size) > TG_SPLIT_SIZE:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                self.arch_proc = Popen(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", path, m_path])
            else:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                self.arch_proc = Popen(["7z", "a", "-mx=0", path, m_path])
            self.arch_proc.wait()
            if self.arch_proc.returncode == -9:
                return
            elif self.arch_proc.returncode != 0:
                LOGGER.error('An error occurred while zipping! Uploading anyway')
                path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
            if self.arch_proc.returncode == 0 and (not self.isQbit or not self.seed or self.uptype == 'tgdrive'):
                try:
                    rmtree(m_path)
                except:
                    osremove(m_path)

        elif self.extract:
            try:
                if ospath.isfile(m_path): # Use 'pextract' and 'extract' to extract different types of compressed files
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                     download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if ospath.isdir(m_path): # Use 7z command to extract the sub-volume dir
                    for dirpath, subdir, files in walk(m_path, topdown=False):
                        for file_ in files:
                            if file_.endswith((".zip", ".7z")) or re_search(r'\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$', file_) \
                               or (file_.endswith(".rar") and not re_search(r'\.part\d+\.rar$', file_)):
                                m_path = ospath.join(dirpath, file_)
                                if self.pswd is not None:
                                    self.ext_proc = Popen(["7z", "x", f"-p{self.pswd}", m_path, f"-o{dirpath}", "-aot"])
                                else:
                                    self.ext_proc = Popen(["7z", "x", m_path, f"-o{dirpath}", "-aot"])
                                self.arch_proc.wait()
                                if self.ext_proc.returncode == -9:
                                    return
                                elif self.ext_proc.returncode != 0:
                                    LOGGER.error('Unable to extract archive splits! Uploading anyway')
                        if self.ext_proc.returncode == 0:
                            for file_ in files:
                                if file_.endswith((".rar", ".zip", ".7z")) or \
                                    re_search(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$', file_):
                                    del_path = ospath.join(dirpath, file_)
                                    osremove(del_path)
                    path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
                else:
                    if self.pswd is not None:
                        self.ext_proc = Popen(["bash", "pextract", m_path, self.pswd])
                    else:
                        self.ext_proc = Popen(["bash", "extract", m_path])
                    self.ext_proc.wait()
                    if self.ext_proc.returncode == -9:
                        return
                    elif self.ext_proc.returncode == 0:
                        LOGGER.info(f"Extracted Path: {path}")
                        osremove(m_path)
                    else:
                        LOGGER.error('Unable to extract archive! Uploading anyway')
                        path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
        else:
            path = f'{DOWNLOAD_DIR}{self.uid}/{name}'


        up_name = path.rsplit('/', 1)[-1]
        if self.uptype == 'tgdrive' and not self.isZip:
            checked = False
            for dirpath, subdir, files in walk(f'{DOWNLOAD_DIR}{self.uid}', topdown=False):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    f_size = ospath.getsize(f_path)
                    if int(f_size) > TG_SPLIT_SIZE:
                        if not checked:
                            checked = True
                            with download_dict_lock:
                                download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                            LOGGER.info(f"Splitting: {up_name}")
                        res = split_file(f_path, f_size, file_, dirpath, TG_SPLIT_SIZE, self)
                        if not res:
                            return
                        osremove(f_path)
        if self.uptype == 'tgdrive':
            size = get_path_size(f'{DOWNLOAD_DIR}{self.uid}')
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            update_all_messages()
            return tg.upload()
        
        up_path = f'{DOWNLOAD_DIR}{self.uid}/{up_name}'
        size = get_path_size(up_path)
        if self.uptype == 'gdrive':
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, self)
            gd_upload_status = UploadStatus(drive, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = gd_upload_status
            update_all_messages()
            drive.upload(up_name)
        elif self.uptype == 'rcdrive':
            LOGGER.info(f"Upload Name: {up_name}")
            rc = RcUploader(up_name, self)
            rc_upload_status = RcUploadStatus(rc, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = rc_upload_status
            update_all_messages()
            rc.upload()
        else:
            size = get_readable_file_size(size)
            LOGGER.info(f"Upload Name: {up_name}")
            total_files = 0
            total_folders = 0
            if ospath.isfile(up_path):
                mime_type = get_mime_type(up_path)
                if ospath.exists(ospath.join(HHD_DIR, up_name)):
                    up_name = f'{randint(0, 1000)}{up_name}'
                    copyfile(up_path, ospath.join(HHD_DIR, up_name))
                else:
                    copyfile(up_path, ospath.join(HHD_DIR, up_name))
            else:
                mime_type = 'Folder'
                for root, dirs, files in walk(up_path):
                    for file in files:
                        if not file.lower().endswith(tuple(EXTENSION_FILTER)):
                            dst_dir = ospath.join(HHD_DIR, root.strip(f'{DOWNLOAD_DIR}{self.uid}/'), file)
                            if ospath.exists(dst_dir):
                                continue
                            else:
                                copyfile(ospath(root,files), dst_dir)
                            total_files += 1
                    total_folders += len(dirs)
            self.onUploadComplete(None, size, total_files, total_folders, mime_type, up_name)


    def onDownloadError(self, error):
        error = error.replace('<', ' ').replace('>', ' ')
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        msg = f"{self.tag} your download has been stopped due to: {error}"
        sendMessage(msg, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)


    def onUploadComplete(self, link: str, size, files, folders, typ, name: str):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)
        msg = f"<b>Name: </b><code>{escape(name)}</code>\n\n<b>Size: </b>{size}"
        if self.uptype == 'tgdrive':
            msg += f'\n<b>Total Files: </b>{folders}'
            if typ != 0:
                msg += f'\n<b>Corrupted Files: </b>{typ}'
            msg += f'\n<b>cc: </b>{self.tag}\n\n'
            if not files:
                sendMessage(msg, self.bot, self.message)
            else:
                fmsg = ''
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        sendMessage(msg + fmsg, self.bot, self.message)
                        sleep(1)
                        fmsg = ''
                if fmsg != '':
                    sendMessage(msg + fmsg, self.bot, self.message)
        elif self.uptype == 'gdrive':
            msg += f'\n\n<b>Type: </b>{typ}'
            if ospath.isdir(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
                msg += f'\n<b>SubFolders: </b>{folders}'
                msg += f'\n<b>Files: </b>{files}'
            msg += f'\n\n<b>cc: </b>{self.tag}'
            buttons = ButtonMaker()
            buttons.buildbutton("☁️ Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            if INDEX_URL is not None:
                url_path = rutils.quote(f'{name}')
                share_url = f'{INDEX_URL}/{url_path}'
                if ospath.isdir(f'{DOWNLOAD_DIR}/{self.uid}/{name}'):
                    share_url += '/'
                    buttons.buildbutton("⚡ Index Link", share_url)
                else:
                    buttons.buildbutton("⚡ Index Link", share_url)
                    if VIEW_LINK:
                        share_urls = f'{INDEX_URL}/{url_path}?a=view'
                        buttons.buildbutton("🌐 View Link", share_urls)
            sendMarkup(msg, self.bot, self.message, InlineKeyboardMarkup(buttons.build_menu(2)))
        elif self.uptype == 'rcdrive':
            msg += f'\n\n<b>Type: </b>{typ}'
            user_id = self.message.from_user.id
            dest_dir = USER_RcDrive.get(user_id)['dest_dir']
            drive_lette = USER_RcDrive.get(user_id)['drive_letter']
            drive_path = ospath.join(dest_dir, name)
            drive_path = b64encode(drive_path.encode()).decode('utf-8')
            msg += f'\n\n<b>Path: </b><code>RcDride:{drive_lette}.{drive_path}</code>'
            if ospath.isdir(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
                msg += f'\n<b>SubFolders: </b>{folders}'
                msg += f'\n<b>Files: </b>{files}'
            msg += f'\n\n<b>cc: </b>{self.tag}'
            LOGGER.info(f'Done Uploading {name}')
            sendMessage(msg, self.bot, self.message)
        else:
            msg += f'\n\n<b>Type: </b>{typ}'
            drive_path = ospath.join(HHD_DIR, name)
            drive_path = b64encode(drive_path.encode()).decode('utf-8')
            msg += f'\n\n<b>Path: </b><code>HhDride:{drive_path}</code>'
            if ospath.isdir(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
                msg += f'\n<b>SubFolders: </b>{folders}'
                msg += f'\n<b>Files: </b>{files}'
            msg += f'\n\n<b>cc: </b>{self.tag}'
            LOGGER.info(f'Done Uploading {name}')
            sendMessage(msg, self.bot, self.message)

        if self.isQbit and self.seed and not self.extract and self.uptype != 'tgdrive':
            if self.isZip:
                try:
                    osremove(f'{DOWNLOAD_DIR}{self.uid}/{name}')
                except:
                    pass
            return
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onUploadError(self, error):
        e_str = error.replace('<', '').replace('>', '')
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        sendMessage(f"{self.tag} {e_str}", self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)

def _mirror(bot, message, isZip=False, extract=False, isQbit=False, uptype='hddrive', pswd=None, multi=0, qbsd=False):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    qbsel = False
    index = 1

    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=3)
        if "s" in [x.strip() for x in args]:
            qbsel = True
            index += 1
        if "d" in [x.strip() for x in args]:
            qbsd = True
            index += 1
        message_args = mesg[0].split(maxsplit=index)
        if len(message_args) > index:
            link = message_args[index].strip()
            if link.isdigit():
                multi = int(link)
                link = ''
            elif link.startswith(("n-name:", "pswd:", "ua:", "sp_con:")):
                link = ''
        else:
            link = ''
    else:
        link = ''

    link = re_split(r"n-name:|pswd:|ua:|sp_con:", link)[0]
    link = link.strip()
    name_args = mesg[0].split('n-name:')
    if len(name_args) > 1:
        name = re_split(r"pswd:|ua:|sp_con:", name_args[-1])[0]
        name = name.strip()
    else:
        name = ''
    pswd_args = mesg[0].split('pswd:')
    if len(pswd_args) > 1:
        pswd = re_split(r"n-name:|ua:|sp_con:", pswd_args[-1])[0]
        pswd = pswd.strip()
    ua_args = mesg[0].split('ua:')
    if len(ua_args) > 1:
        ua = re_split(r"n-name:|pswd:|sp_con:", ua_args[-1])[0]
        ua = ua.strip()
    else:
        ua = 'Wget/1.12'
    sp_con_args = mesg[0].split('sp_con:')
    if len(sp_con_args) > 1:
        sp_con = re_split(r"n-name:|pswd:|ua:", sp_con_args[-1])[0]
        sp_con = int(sp_con.strip())
    else:
        sp_con = 10

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        file = None
        media_array = [reply_to.document, reply_to.video, reply_to.audio]
        for i in media_array:
            if i is not None:
                file = i
                break

        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

        if not is_url(link) and not is_magnet(link) or len(link) == 0:
            if file is None:
                reply_text = reply_to.text.split(maxsplit=1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_text
            elif file.mime_type != "application/x-bittorrent" and not isQbit:
                listener = MirrorListener(bot, message, isZip, extract, isQbit, uptype, pswd, tag)
                Thread(target=TelegramDownloadHelper(listener).add_download, args=(message, f'{DOWNLOAD_DIR}{listener.uid}/', name)).start()
                if multi > 1:
                    sleep(4)
                    nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
                    nextmsg = sendMessage(message_args[0], bot, nextmsg)
                    nextmsg.from_user.id = message.from_user.id
                    multi -= 1
                    sleep(4)
                    Thread(target=_mirror, args=(bot, nextmsg, isZip, extract, isQbit, uptype, pswd, multi)).start()
                return
            else:
                link = file.get_file().file_path

    if not is_url(link) and not is_magnet(link) and not ospath.exists(link):
        help_msg = "<b>Send link along with command line:</b>"
        help_msg += "\n<code>/command</code> {link} n-name:xx pswd:xx[zip/unzip] ua:xx sp_con:xx"
        help_msg += "\n\n<b>By replying to link or file:</b>"
        help_msg += "\n<code>/command</code> n-name:xx pswd:xx[zip/unzip] ua:xx sp_con:xx"
        help_msg += "\n\n<b>Direct link authorization:</b>"
        help_msg += "\n<code>/command</code> {link} n-name:xx pswd:xx\nusername\npassword"
        help_msg += "\n\n<b>Qbittorrent selection and seed:</b>"
        help_msg += "\n<code>/qbcommand</code> <b>s</b>(for selection) <b>d</b>(for seeding) {link} or by replying to {file/link}"
        help_msg += "\n\n<b>Multi links only by replying to first link or file:</b>"
        help_msg += "\n<code>/command</code> 10(number of links/files)"
        return sendMessage(help_msg, bot, message)

    LOGGER.info(link)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
            and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            try:
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    return sendMessage(str(e), bot, message)
    elif isQbit and not is_magnet(link):
        if link.endswith('.torrent') or "https://api.telegram.org/file/" in link:
            content_type = None
        else:
            content_type = get_content_type(link)
        if content_type is None or re_match(r'application/x-bittorrent|application/octet-stream', content_type):
            try:
                resp = rget(link, timeout=10, headers={'user-agent': 'Wget/1.12'})
                if resp.status_code == 200:
                    file_name = str(time()).replace(".", "") + ".torrent"
                    with open(file_name, "wb") as t:
                        t.write(resp.content)
                    link = str(file_name)
                else:
                    return sendMessage(f"{tag} ERROR: link got HTTP response: {resp.status_code}", bot, message)
            except Exception as e:
                error = str(e).replace('<', ' ').replace('>', ' ')
                if error.startswith('No connection adapters were found for'):
                    link = error.split("'")[1]
                else:
                    LOGGER.error(str(e))
                    return sendMessage(tag + " " + error, bot, message)
        else:
            msg = "Qb commands for torrents only. if you are trying to dowload torrent then report."
            return sendMessage(msg, bot, message)

    listener = MirrorListener(bot, message, isZip, extract, isQbit, uptype, pswd, tag, qbsd)

    if is_gdrive_link(link):
        if not isZip and not extract and uptype != 'gdrive':
            gmsg = f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand} to extracts Google Drive archive file"
            sendMessage(gmsg, bot, message)
        else:
            Thread(target=add_gd_download, args=(link, listener)).start()
    elif is_mega_link(link):
        Thread(target=add_mega_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}/', listener)).start()
    elif isQbit and (is_magnet(link) or ospath.exists(link)):
        Thread(target=QbDownloader(listener).add_qb_torrent, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', qbsel)).start()
    else:
        if len(mesg) > 1:
            try:
                ussr = mesg[1]
            except:
                ussr = ''
            try:
                pssw = mesg[2]
            except:
                pssw = ''
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        Thread(target=add_aria2c_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, auth, ua, sp_con)).start()

    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        msg = message_args[0]
        if len(mesg) > 2:
            msg += '\n' + mesg[1] + '\n' + mesg[2]
        nextmsg = sendMessage(msg, bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        sleep(4)
        Thread(target=_mirror, args=(bot, nextmsg, isZip, extract, isQbit, uptype, pswd, multi)).start()


def _button_gen(update, context):
    msg_id = update.message.message_id
    buttons = button_build.ButtonMaker()
    buttons.sbutton("G-drive", f"{listener_dict[msg_id][2]}_gdrive_{msg_id}")
    buttons.sbutton("Tg-drive", f"{listener_dict[msg_id][2]}_tgdrive_{msg_id}")
    buttons.sbutton("Rc-drive", f"{listener_dict[msg_id][2]}_rcdrive_{msg_id}")
    buttons.sbutton("Hd-drive", f"{listener_dict[msg_id][2]}_hddrive_{msg_id}")
    buttons.sbutton("Cancel Download", f"{listener_dict[msg_id][2]}_cancel_{msg_id}")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup("Choose option to storage.", context.bot, update.message, button)

def _button_callback(update, context):
    query = update.callback_query
    msg = query.message
    data=query.data.split('_')
    user_id = query.from_user.id
    task_id = int(data[2])
    try:
        task_info = listener_dict[task_id]
    except:
        return editMessage("This is an old task", msg)
    uid = task_info[1]
    if user_id != uid and not CustomFilters._owner_query(user_id):
        return query.answer(text="This task is not for you!", show_alert=True)
    if data[1] == "cancel":
        query.answer()
        LOGGER.info(f"The download has been canceled")
        del listener_dict[task_id]
        return editMessage(f"The download has been canceled.", msg)
    elif data[1] == "gdrive":
        if not USER_GdDrive.get('parent_id'):
            return query.answer(text="G-drive not setting!", show_alert=True)
        else:
            query.answer()
            query.message.delete()
            uptype='gdrive'      
    elif data[1] == "tgdrive":
        query.answer()
        query.message.delete()
        uptype='tgdrive'
    elif data[1] == "rcdrive":
        if not USER_RcDrive.get(user_id):
            return query.answer(text="Rclone config not setting! Please enter /rcdrive to complete rclone init.", show_alert=True)
        else:
            query.answer()
            query.message.delete()
            uptype='rcdrive'
    else:
        if not CustomFilters._owner_query(user_id):
            return query.answer(text="Only owner can upload Hddrive!", show_alert=True)
        else:
            query.answer()
            query.message.delete()
            uptype='hddrive'
    del listener_dict[task_id]
    _mirror(context.bot, task_info[0], uptype=uptype, isZip=task_info[3], extract=task_info[4], isQbit=task_info[5])


def mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'upmirror', False, False, False] #isZip=task_info[3], extract=task_info[4], isQbit=task_info[5]
    _button_gen(update, context)
def mirror_callback(update, context):
    _button_callback(update, context)

def unzip_mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'upextract', False, True, False]
    _button_gen(update, context)
def unzip_mirror_callback(update, context):
    _button_callback(update, context)

def zip_mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'uparchive', True, False, False]
    _button_gen(update, context)
def zip_mirror_callback(update, context):
    _button_callback(update, context)

def qb_mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'upqbit', False, False, True]
    _button_gen(update, context)
def qb_mirror_callback(update, context):
    _button_callback(update, context)

def qb_unzip_mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'upqbext', False, True, True]
    _button_gen(update, context)
def qb_unzip_mirror_callback(update, context):
    _button_callback(update, context)

def qb_zip_mirror(update, context):
    msg = update.message
    user_id = msg.from_user.id
    msg_id = msg.message_id
    listener_dict[msg_id] = [msg, user_id, 'upqbach', True, False, True]
    _button_gen(update, context)
def qb_zip_mirror_callback(update, context):
    _button_callback(update, context)


mirror_handler = CommandHandler(BotCommands.MirrorCommand, mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
unzip_mirror_handler = CommandHandler(BotCommands.UnzipMirrorCommand, unzip_mirror,
                                      filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
zip_mirror_handler = CommandHandler(BotCommands.ZipMirrorCommand, zip_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
qb_mirror_handler = CommandHandler(BotCommands.QbMirrorCommand, qb_mirror,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
qb_unzip_mirror_handler = CommandHandler(BotCommands.QbUnzipMirrorCommand, qb_unzip_mirror,
                                         filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
qb_zip_mirror_handler = CommandHandler(BotCommands.QbZipMirrorCommand, qb_zip_mirror,
                                       filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

mirror_callback_handler = CallbackQueryHandler(mirror_callback, pattern="upmirror", run_async=True)
unzip_mirror_callback_handler = CallbackQueryHandler(unzip_mirror_callback, pattern="upextract", run_async=True)
zip_mirror_callback_handler = CallbackQueryHandler(zip_mirror_callback, pattern="uparchive", run_async=True)
qb_mirror_callback_handler = CallbackQueryHandler(qb_mirror_callback, pattern="upqbit", run_async=True)
qb_unzip_mirror_callback_handler = CallbackQueryHandler(qb_unzip_mirror_callback, pattern="upqbext", run_async=True)
qb_zip_mirror_callback_handler = CallbackQueryHandler(qb_zip_mirror_callback, pattern="upqbach", run_async=True)


dispatcher.add_handler(mirror_handler)
dispatcher.add_handler(unzip_mirror_handler)
dispatcher.add_handler(zip_mirror_handler)
dispatcher.add_handler(qb_mirror_handler)
dispatcher.add_handler(qb_unzip_mirror_handler)
dispatcher.add_handler(qb_zip_mirror_handler)
dispatcher.add_handler(mirror_callback_handler)
dispatcher.add_handler(unzip_mirror_callback_handler)
dispatcher.add_handler(zip_mirror_callback_handler)
dispatcher.add_handler(qb_mirror_callback_handler)
dispatcher.add_handler(qb_unzip_mirror_callback_handler)
dispatcher.add_handler(qb_zip_mirror_callback_handler)