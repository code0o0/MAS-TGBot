from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import path as ospath, listdir as oslistdir, environ
from requests import get as rget
from subprocess import Popen, run as srun
from time import sleep, time
from threading import Thread, Lock
from dotenv import load_dotenv
from pyrogram import Client, enums
from asyncio import get_event_loop

main_loop = get_event_loop()

faulthandler_enable()
setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)
LOGGER = getLogger(__name__)


load_dotenv('/usr/src/app/config/config.env', override=True)

def getConfig(name, default_str = ''):
    var = environ.get(name, '')
    if len(var) == 0:
        return default_str
    else:
        return var
try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

# REQUIRED CONFIG
try:
    for var in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH", "DOWNLOAD_DIR"]:
        value = getConfig(var)
        if not value:
            raise KeyError
except:
    log_error("One or more REQUIRED CONFIG variables missing! Exiting now")
    exit(1)
BOT_TOKEN = getConfig('BOT_TOKEN')
OWNER_ID = int(getConfig('OWNER_ID'))
TELEGRAM_API = getConfig('TELEGRAM_API')
TELEGRAM_HASH = getConfig('TELEGRAM_HASH')
DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
if not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL', '5'))
AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION', '20'))
CMD_INDEX = getConfig('CMD_INDEX')
LOGGER.info("Generating BOT_SESSION_STRING")
app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)


# OPTIONAL CONFIG
AUTHORIZED_CHATS = set([int(id.strip()) for id in getConfig('AUTHORIZED_CHATS').split() if len(id) > 0])
SUDO_USERS = set([int(id.strip()) for id in getConfig('SUDO_USERS').split() if len(id) > 0])
IGNORE_PENDING_REQUESTS = getConfig("IGNORE_PENDING_REQUESTS")
if IGNORE_PENDING_REQUESTS.lower() == 'true':
    IGNORE_PENDING_REQUESTS = True
else:
    IGNORE_PENDING_REQUESTS = False


# STORAGE CONF
HHD_DIR = '/usr/src/app/storage'
CONFIG_DIR = '/usr/src/app/config'
DB_URI = '/usr/src/app/config/data.db'


# UPLOAD G-DRIVE
USER_GdDrive = {}


# UPLOAD TELEGRAM
AS_DOC_USERS = set()
AS_MEDIA_USERS = set()
TG_SPLIT_SIZE = min(int(getConfig('TG_SPLIT_SIZE','2097151000')), 2097151000)
AS_DOCUMENT = getConfig('AS_DOCUMENT')
if AS_DOCUMENT.lower() == 'true':
    AS_DOCUMENT = True
else:
    AS_DOCUMENT = False
try:
    EQUAL_SPLITS = getConfig('EQUAL_SPLITS')
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'
except:
    EQUAL_SPLITS = False
CUSTOM_FILENAME = getConfig('CUSTOM_FILENAME', None)


# UPLOAD RCLONE
USER_RcDrive = {}


# DIRECT-INDEX
try:
    INDEX_URL = getConfig('INDEX_URL').rstrip("/")
    if len(INDEX_URL) == 0:
        raise KeyError
except:
    INDEX_URL = None


# DOWNLOAD-SETTING
STATUS_LIMIT = int(getConfig('STATUS_LIMIT', '4'))
try:
    TORRENT_TIMEOUT = getConfig('TORRENT_TIMEOUT')
    if len(TORRENT_TIMEOUT) == 0:
        raise KeyError
    TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
except:
    TORRENT_TIMEOUT = None
EXTENSION_FILTER = set()
try:
    fx = getConfig('EXTENSION_FILTER')
    if len(fx) > 0:
        fx = fx.split()
        for x in fx:
            EXTENSION_FILTER.add(x.strip().lower())
except:
    pass
try:
    INCOMPLETE_TASK_NOTIFIER = getConfig('INCOMPLETE_TASK_NOTIFIER')
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'
except:
    INCOMPLETE_TASK_NOTIFIER = False


# qBittorrent
try:
    BASE_URL = getConfig('BASE_URL_OF_BOT').rstrip("/")
    if len(BASE_URL) == 0:
        raise KeyError
except:
    log_warning('BASE_URL_OF_BOT not provided!')
    BASE_URL = None

SERVER_PORT = int(getConfig('SERVER_PORT','80'))
Popen([f"gunicorn web.wserver:app --bind 0.0.0.0:{SERVER_PORT}"], shell=True)
srun(["qbittorrent-nox", "-d", "--profile=."])
try:
    WEB_PINCODE = getConfig('WEB_PINCODE')
    WEB_PINCODE = WEB_PINCODE.lower() == 'true'
except:
    WEB_PINCODE = False
try:
    QB_SEED = getConfig('QB_SEED')
    QB_SEED = QB_SEED.lower() == 'true'
except:
    QB_SEED = False
def get_client():
    return qbClient(host="localhost", port=8090)


# Private Files
UPTOBOX_TOKEN = getConfig('UPTOBOX_TOKEN', None)
CRYPT = getConfig('CRYPT', None)
try:
    YT_COOKIES_URL = getConfig('YT_COOKIES_URL')
    if len(YT_COOKIES_URL) == 0:
        raise KeyError
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open('cookies.txt', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download cookies.txt, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")
except:
    pass
try:
    NETRC_URL = getConfig('NETRC_URL')
    if len(NETRC_URL) == 0:
        raise KeyError
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open('.netrc', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")
except:
    pass
if not ospath.exists('.netrc'):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])


# MEGA
MEGA_API_KEY = getConfig('MEGA_API_KEY', None)
MEGA_EMAIL_ID = getConfig('MEGA_EMAIL_ID', None)
MEGA_PASSWORD = getConfig('MEGA_PASSWORD', None)


# RSS
RSS_COMMAND = getConfig('RSS_COMMAND', None)
try:
    RSS_CHAT_ID = getConfig('RSS_CHAT_ID')
    if len(RSS_CHAT_ID) == 0:
        raise KeyError
    RSS_CHAT_ID = int(RSS_CHAT_ID)
except:
    RSS_CHAT_ID = None
RSS_DELAY = int(getConfig('RSS_DELAY', '900'))
USER_SESSION_STRING = getConfig('USER_SESSION_STRING', None)
if not USER_SESSION_STRING:
    rss_session = Client(name='rss_session', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)


# Buttons
try:
    VIEW_LINK = getConfig('VIEW_LINK')
    VIEW_LINK = VIEW_LINK.lower() == 'true'
except:
    VIEW_LINK = False

# Torrent Search
SEARCH_LIMIT = int(getConfig('SEARCH_LIMIT', '0'))
try:
    SEARCH_API_LINK = getConfig('SEARCH_API_LINK').rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        raise KeyError
except:
    SEARCH_API_LINK = None
try:
    seplugin_path = ospath.join('/usr/src/app', 'qBittorrent/search-plugins')
    SEARCH_PLUGINS = [ospath.join(seplugin_path, x) for x in oslistdir(seplugin_path) if ospath.isfile(ospath.join(seplugin_path, x))]
    if len(SEARCH_PLUGINS) == 0:
        raise KeyError
except:
    SEARCH_PLUGINS = None


# Set golbal var
Interval = []
download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id - Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id - Value: An object of Status
download_dict = {}
# key: rss_title - value: [rss_feed, last_link, last_title, filter]
rss_dict = {}


# Aria2
srun(["chmod", "+x", "aria.sh"])
srun(["./aria.sh"], shell=True)
sleep(0.5)
aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret="",
    )
)

def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {'dir': dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(10)
        for download in downloads:
            aria2.remove([download], force=True, files=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")
Thread(target=aria2c_init).start()
sleep(1.5)

updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
