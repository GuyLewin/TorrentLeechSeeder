import os
import time
import bencode
import logging

import utils


class Torrent(object):
    def __init__(self, path):
        with open(path, "rb") as f:
            torrent_file_content = f.read()

        self.torrent_file = bencode.bdecode(torrent_file_content)
        self.total_length = 0
        self.piece_length = self.torrent_file['info']['piece length']
        self.pieces = self.torrent_file['info']['pieces']
        self.info_hash = utils.sha1_hash(str(bencode.bencode(self.torrent_file['info'])))
        self.peer_id = Torrent.generate_peer_id()
        self.announce_list = self.get_trackers()
        self.file_names = []

        self.get_files()

        if self.total_length % self.piece_length == 0:
            self.number_of_pieces = self.total_length / self.piece_length
        else:
            self.number_of_pieces = (self.total_length / self.piece_length) + 1

        logging.debug(self.announce_list)
        logging.debug(self.file_names)

        assert(self.total_length > 0)
        assert(len(self.file_names) > 0)

    def get_files(self):
        root = self.torrent_file['info']['name']

        if "files" in self.torrent_file['info']:
            if not os.path.exists(root):
                os.mkdir(root, 0766)

            for f in self.torrent_file['info']['files']:
                file_path = os.path.join(root, *f["path"])

                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))

                self.file_names.append({"path": file_path, "length": f["length"]})
                self.total_length += f["length"]

        else:
            self.file_names.append({"path": root , "length": self.torrent_file['info']['length']})
            self.total_length = self.torrent_file['info']['length']

    def get_trackers(self):
        if "announce-list" in self.torrent_file:
            return self.torrent_file['announce-list']
        else:
            return [[self.torrent_file['announce']]]

    @staticmethod
    def generate_peer_id():
        seed = str(time.time())
        return utils.sha1_hash(seed)
