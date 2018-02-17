import os
import logging
import subprocess

import utils
from torrentleech_api.utils import size_float_to_str

ARIA2C_INITIALIZATION_LINES = 5


class Aria2cManager(object):
    def __init__(self, download_dir, download_dir_max_size, aria2c_path):
        self._download_dir = download_dir
        if not os.path.exists(download_dir):
            logging.debug("Creating directory structure {0}".format(download_dir))
            os.makedirs(download_dir)
        self._download_dir_max_size = download_dir_max_size
        self._aria2c_path = aria2c_path
        self._running_aria2c_processes = []

    def get_space_left(self, log=False):
        space_left = self._download_dir_max_size - utils.dir_size(self._download_dir)
        if log:
            if space_left >= 0:
                logging.info("Space left on {0}: {1}".format(self._download_dir, size_float_to_str(space_left)))
            else:
                logging.info("{0} is bigger than max size by {1}".format(
                    self._download_dir, size_float_to_str(-space_left)
                ))
        return space_left

    def download_torrent(self, torrent_file_path):
        p = subprocess.Popen([
            self._aria2c_path, "-T", torrent_file_path, "-d", self._download_dir, "--seed-ratio=0.0"
        ], stdout=subprocess.PIPE, bufsize=1)
        lines_read_after_file_allocation = 0
        file_allocation_started = False
        logging.info("Making sure we're able to download the torrent...")
        while p.poll() is None:
            if lines_read_after_file_allocation > ARIA2C_INITIALIZATION_LINES:
                logging.info("Torrent is downloading in the background. Moving on")
                # aria2c printed 15 lines without failing. Assuming it's running OK
                self._running_aria2c_processes.append(p)
                return p
            stdout_line = p.stdout.readline()
            if "FileAlloc" in stdout_line:
                file_allocation_started = True
            elif file_allocation_started:
                # FileAlloc doesn't appear in output anymore, that means we are actually starting to download
                lines_read_after_file_allocation += 1
            if "Tracker returned failure" in stdout_line:
                logging.info("Reached maximal amount of simultaneous torrents")
                return None
        logging.info("aria2c died from an unknown reason")
        return None
