import bitstring
import logging
from threading import Thread
from pubsub import pub

import piece


class PiecesManager(Thread):
    def __init__(self, torrent):
        Thread.__init__(self)
        self.torrent = torrent
        self.pieces_completed = False

        self.number_of_pieces = torrent.number_of_pieces

        self.bitfield = bitstring.BitArray(self.number_of_pieces)
        self.pieces = self.generate_pieces()

        self.files = self.get_files()

        for f in self.files:
            piece_id = f['piece_id']
            self.pieces[piece_id].files.append(f)

        # Create events
        pub.subscribe(self.receive_block_piece, 'PiecesManager.Piece')
        pub.subscribe(self.update_bitfield, 'PiecesManager.PieceCompleted')

    def update_bitfield(self, piece_index):
        self.bitfield[piece_index] = 1

    def receive_block_piece(self, piece):
        piece_index, piece_offset, piece_data = piece
        self.pieces[int(piece_index)].set_block(piece_offset, piece_data)

    def generate_pieces(self):
        pieces = []

        for i in range(self.number_of_pieces):
            start = i * 20
            end = start + 20

            if i == (self.number_of_pieces - 1):
                piece_length = self.torrent.total_length - (self.number_of_pieces - 1) * self.torrent.piece_length
                pieces.append(piece.Piece(i, piece_length, self.torrent.pieces[start:end]))
            else:
                pieces.append(piece.Piece(i, self.torrent.piece_length, self.torrent.pieces[start:end]))
        return pieces

    def are_pieces_completed(self):
        for piece in self.pieces:
            if not piece.finished:
                return False

        self.pieces_completed = True
        logging.info("File(s) downloaded")
        return True

    def get_files(self):
        files = []
        piece_offset = 0
        piece_size_used = 0

        for f in self.torrent.file_names:
            current_size_file = f["length"]
            file_offset = 0

            while current_size_file > 0:
                piece_id = piece_offset / self.torrent.piece_length
                piece_size = self.pieces[piece_id].piece_size - piece_size_used

                if current_size_file - piece_size < 0:
                    f = {
                        "length": current_size_file,
                        "piece_id": piece_id,
                        "file_offset": file_offset,
                        "piece_offset": piece_size_used,
                        "path": f["path"]
                    }
                    piece_offset += current_size_file
                    file_offset + current_size_file
                    piece_size_used += current_size_file
                    current_size_file = 0
                else:
                    current_size_file -= piece_size
                    f = {
                        "length": piece_size,
                        "piece_id": piece_id,
                        "file_offset": file_offset,
                        "piece_offset": piece_size_used,
                        "path": f["path"]
                    }
                    piece_offset += piece_size
                    file_offset += piece_size
                    piece_size_used = 0

                files.append(f)
        return files

    def get_block(self, piece_index, block_offset, block_length):
        for piece in self.pieces:
            if piece_index == piece.pieceIndex:
                if piece.finished:
                    return piece.get_block(block_offset, block_length)
                else:
                    break

        return None
