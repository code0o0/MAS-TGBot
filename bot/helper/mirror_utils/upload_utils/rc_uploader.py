from logging import getLogger, ERROR
import time
from os import path as ospath
from os import walk as oswalk
import subprocess
import re
from bot import DOWNLOAD_DIR, EXTENSION_FILTER, USER_Drive
from bot.helper.ext_utils.bot_utils import get_readable_file_size, setInterval
from bot.helper.ext_utils.fs_utils import get_mime_type, get_path_size

LOGGER = getLogger(__name__)
getLogger('rcupload').setLevel(ERROR)

class RcUploader:

    def __init__(self, name=None, listener=None):
        self.__listener = listener
        self.user_id = self.__listener.message.from_user.id
        self.uploaded_bytes = 0
        self.__file_uploaded_bytes = 0
        self.__chunk_size = 0
        self.is_cancelled = False
        self.is_errored = False
        self.updater = None
        self.name = name
        self.update_interval = 3
        self.total_time = 0
        self.__total_files = 0
        self.__total_folders = 0


    def __upload_file(self, file_path, remote_path):
        sleeps = False
        rclone_copy_cmd = ['rclone', 'copy', '-P', '--cache-chunk-size', '64Mi', '--stats', '2s', f"--config={USER_Drive.get(self.user_id)['rc_conf_path']}", str(file_path), f"{USER_Drive.get(self.user_id)['drive_letter']}:{remote_path}"]
        self.rclone_pr = subprocess.Popen(rclone_copy_cmd, stdout=(subprocess.PIPE), stderr=(subprocess.PIPE))
        while True:
            if self.is_cancelled:
                break
            if self.rclone_pr.poll() != None:
                break
            data = self.rclone_pr.stdout.readline().decode().strip()
            re_data=re.findall(r'Transferred:.*?(\d.*?)B/s.*?ETA', data)
            if re_data:
                sleeps = True
                nstr = re.split(r',|\s',re_data[-1])
                uploaded_num= float(nstr[0].strip())
                if nstr[1].lower() == 'kib':
                    self.uploaded_bytes = int(uploaded_num*1024)
                elif nstr[1].lower() == 'mib':
                    self.uploaded_bytes = int(uploaded_num*1024*1024)
                elif nstr[1].lower() == 'gib':
                    self.uploaded_bytes = int(uploaded_num*1024*1024*1024)
                elif nstr[1].lower() == 'tib':
                    self.uploaded_bytes = int(uploaded_num*1024*1024*1024*1024)
            if sleeps:
                sleeps = False
                time.sleep(1)
                self.rclone_pr.stdout.flush()

        if self.rclone_pr.poll() != 0:
            error = self.rclone_pr.stderr.readline().decode().strip()
            LOGGER.error(f"Rclone upload error: {error}" )
            return error

        return None
    
    def upload(self):
        file_dir = f"{DOWNLOAD_DIR}{self.__listener.message.message_id}"
        file_path = f"{file_dir}/{self.name}"
        size = get_readable_file_size(get_path_size(file_path))
        LOGGER.info("Uploading File: " + file_path)
        self.updater = setInterval(self.update_interval, self._on_upload_progress)
        try:
            if ospath.isfile(file_path):
                mime_type = get_mime_type(file_path)
                self.__total_files += 1
                result = self.__upload_file(file_path, USER_Drive.get(self.user_id)['dest_dir'])
                if self.is_cancelled:
                    raise Exception('Upload has been manually cancelled')
                if result:
                    raise Exception(result)
                LOGGER.info("Uploaded To Drive: " + file_path)
            else:
                mime_type = 'Folder'
                for root, dirs, files in oswalk(file_path):
                    for file in files:
                        if not file.lower().endswith(tuple(EXTENSION_FILTER)):
                            self.__total_files += 1
                    self.__total_folders += len(dirs)
                remote_path = ospath.join(USER_Drive.get(self.user_id)['dest_dir'], self.name)
                result = self.__upload_file(file_path, remote_path)
                if self.is_cancelled:
                    raise Exception('Upload has been manually cancelled!')
                if result:
                    raise Exception(result)
                LOGGER.info("Uploaded To Drive: " + self.name)
        except Exception as err:
            exception_name = err.__class__.__name__
            LOGGER.error(f"{err}. Exception Name: {exception_name}")
            self.__listener.onUploadError(str(err))
            self.is_errored = True
        finally:
            self.updater.cancel()
            if self.is_cancelled:
                if mime_type == 'Folder':
                    LOGGER.info("Deleting uploaded data from Drive...")
                    subprocess.run(['rclone', 'purge', f"--config={USER_Drive.get(self.user_id)['rc_conf_path']}", f"{USER_Drive.get(self.user_id)['drive_letter']}:{remote_path}"])
                return
            elif self.is_errored:
                return
        self.__listener.onUploadComplete(None, size, self.__total_files, self.__total_folders, mime_type, self.name)
    
    @property
    def speed(self):
        try:
            return self.__chunk_size / self.update_interval
        except ZeroDivisionError:
            return 0

    def _on_upload_progress(self):
        self.__chunk_size = self.uploaded_bytes - self.__file_uploaded_bytes
        self.__file_uploaded_bytes = self.uploaded_bytes
        self.total_time += self.update_interval
    
    def cancel_download(self):
        self.is_cancelled = True
        self.rclone_pr.kill()
        LOGGER.info(f"Cancelling Upload: {self.name}")
        self.__listener.onUploadError('your upload has been stopped and uploaded data has been deleted!')
