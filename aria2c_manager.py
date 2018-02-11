import os
import subprocess


def _dir_size(dir_to_calc):
    total_size = 0
    for dir_path, dir_names, file_names in os.walk(dir_to_calc):
        for f in file_names:
            fp = os.path.join(dir_path, f)
            total_size += os.path.getsize(fp)
    return total_size


class Aria2cManager(object):
    def __init__(self, download_dir, download_dir_max_size, aria2c_path):
        self._download_dir = download_dir
        self._download_dir_max_size = download_dir_max_size
        self._aria2c_path = aria2c_path
        self._running_aria2c_processes = []

    def get_space_left(self):
        return self._download_dir_max_size - _dir_size(self._download_dir)

    def download_torrent(self, torrent_file_path):
        self._running_aria2c_processes.append(subprocess.Popen([
            self._aria2c_path, "-T", torrent_file_path, "-d", self._download_dir
        ]))
