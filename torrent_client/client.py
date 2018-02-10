import time
import Queue
import logging

import torrent
import tracker
import peer_seeker
import peers_manager
import pieces_manager

# TODO REMOVE
logging.basicConfig(level=logging.DEBUG)


class Client(object):
    def __init__(self):
        new_peers_queue = Queue.Queue()

        self.torrent = torrent.Torrent("/Users/guylewin/Downloads/31C62DE92DCF9FF8CE4CC0D77E073C3C1FD9091E.torrent", "/tmp")
        self.tracker = tracker.Tracker(self.torrent, new_peers_queue)

        self.peer_seeker = peer_seeker.PeerSeeker(new_peers_queue, self.torrent)
        self.pieces_manager = pieces_manager.PiecesManager(self.torrent)
        self.peers_manager = peers_manager.PeersManager(self.torrent, self.pieces_manager)

        self.peers_manager.start()
        logging.info("Peers-manager Started")

        self.peer_seeker.start()
        logging.info("Peer-seeker Started")

        self.pieces_manager.start()
        logging.info("Pieces-manager Started")

    def start(self):
        old = 0

        while not self.pieces_manager.are_pieces_completed():
            if len(self.peers_manager.unchoked_peers) > 0:
                for piece in self.pieces_manager.pieces:
                    if not piece.finished:
                        piece_index = piece.piece_index

                        peer = self.peers_manager.get_unchoked_peer(piece_index)
                        if not peer:
                            continue

                        data = self.pieces_manager.pieces[piece_index].get_empty_block()

                        if data:
                            index, offset, length = data
                            self.peers_manager.request_new_piece(peer, index, offset, length)

                        piece.is_complete()

                        for block in piece.blocks:
                            if (int(time.time()) - block[3]) > 8 and block[0] == "Pending":
                                block[0] = "Free"
                                block[3] = 0

                b = 0
                for i in range(self.pieces_manager.number_of_pieces):
                    for j in range(self.pieces_manager.pieces[i].num_blocks):
                        if self.pieces_manager.pieces[i].blocks[j][0] == "Full":
                            b += len(self.pieces_manager.pieces[i].blocks[j][2])
                if b == old:
                    continue

                old = b
                print "Number of peers: ", len(self.peers_manager.unchoked_peers), \
                    " Completed: ", float((float(b) / self.torrent.total_length) * 100), "%", \
                    " Seeded: {} bytes".format(self.peers_manager.seeded)

            time.sleep(0.1)

Client().start()