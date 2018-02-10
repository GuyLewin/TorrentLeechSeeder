import math
import time
import logging
from pubsub import pub

import utils

BLOCK_SIZE = 2 ** 14


class Piece(object):
    def __init__(self, piece_index, piece_size, piece_hash):
        self.piece_index = piece_index
        self.piece_size = piece_size
        self.piece_hash = piece_hash
        self.finished = False
        self.files = []
        self.piece_data = ""
        self.num_blocks = int(math.ceil(float(piece_size) / BLOCK_SIZE))
        self.blocks = []
        self.init_blocks()

    def init_blocks(self):
        self.blocks = []

        if self.num_blocks > 1:
            for i in range(self.num_blocks):
                    self.blocks.append(["Free", BLOCK_SIZE, "", 0])

            # Last block of last piece, the special block
            if (self.piece_size % BLOCK_SIZE) > 0:
                self.blocks[self.num_blocks-1][1] = self.piece_size % BLOCK_SIZE

        else:
            self.blocks.append(["Free", int(self.piece_size), "", 0])

    def set_block(self, offset, data):
        if not self.finished:
            if offset == 0:
                index = 0
            else:
                index = offset / BLOCK_SIZE

            self.blocks[index][2] = data
            self.blocks[index][0] = "Full"

            self.is_complete()

    def get_block(self, block_offset, block_length):
        return self.piece_data[block_offset:block_length]

    def get_empty_block(self):
        if not self.finished:
            block_index = 0
            for block in self.blocks:
                if block[0] == "Free":
                    block[0] = "Pending"
                    block[3] = int(time.time())
                    return self.piece_index, block_index * BLOCK_SIZE, block[1]
                block_index += 1

        return False

    def are_free_blocks_left(self):
        for block in self.blocks:
            if block[0] == "Free":
                return True
        return False

    def is_complete(self):
        # If there is at least one block Free|Pending -> Piece not complete -> return false
        for block in self.blocks:
            if block[0] == "Free" or block[0] == "Pending":
                return False

        # Before returning True, we must check if hashes match
        data = self.assemble_data()
        if self.is_hash_piece_correct(data):
            self.finished = True
            self.piece_data = data
            self.write_files_to_disk()
            pub.sendMessage('PiecesManager.PieceCompleted', pieceIndex=self.piece_index)
            return True

        else:
            return False

    @staticmethod
    def write_function(file_path, data, offset):
        try:
            f = open(file_path, 'r+b')
        except IOError:
            f = open(file_path, 'wb')
        f.seek(offset)
        f.write(data)
        f.close()

    def write_files_to_disk(self):
        for f in self.files:
            file_path = f["path"]
            file_offset = f["file_offset"]
            piece_offset = f["piece_offset"]
            length = f["length"]

            Piece.write_function(file_path, self.piece_data[piece_offset:piece_offset + length], file_offset)

    def assemble_data(self):
        buf = ""
        for block in self.blocks:
            buf += block[2]
        return buf

    def is_hash_piece_correct(self, data):
        if utils.sha1_hash(data) == self.piece_hash:
            return True
        else:
            logging.warning("Error Piece Hash")
            logging.debug("{}: {}".format(utils.sha1_hash(data), self.piece_hash))
            self.init_blocks()
            return False
