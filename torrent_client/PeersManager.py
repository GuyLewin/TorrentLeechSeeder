import select
import logging
from threading import Thread
from pubsub import pub

import utils
import RarestPieces


class PeersManager(Thread):
    def __init__(self, torrent, pieces_manager):
        Thread.__init__(self)
        self.peers = []
        self.unchoked_peers = []
        self.torrent = torrent
        self.pieces_manager = pieces_manager
        self.rarest_pieces = RarestPieces.RarestPieces(pieces_manager)

        self.pieces_by_peer = []
        for i in range(self.pieces_manager.number_of_pieces):
            self.pieces_by_peer.append([0, []])

        # Events
        pub.subscribe(self.add_peer, 'PeersManager.newPeer')
        pub.subscribe(self.add_unchoked_peer, 'PeersManager.peerUnchoked')
        pub.subscribe(self.handle_peer_requests, 'PeersManager.PeerRequestsPiece')
        pub.subscribe(self.peers_bitfield, 'PeersManager.updatePeersBitfield')

    def peers_bitfield(self, bitfield=None, peer=None, piece_index=None):
        if piece_index is not None:
            self.pieces_by_peer[piece_index] = ["", []]
            return

        for i in range(len(self.pieces_by_peer)):
            if bitfield[i] == 1 and peer not in self.pieces_by_peer[i][1] and not self.pieces_by_peer[i][0] == "":
                self.pieces_by_peer[i][1].append(peer)
                self.pieces_by_peer[i][0] = len(self.pieces_by_peer[i][1])

    def get_unchoked_peer(self, index):
        for peer in self.unchoked_peers:
            if peer.has_piece(index):
                return peer

        return False

    def run(self):
        while True:
            self.start_connection_to_peers()
            read = [p.socket for p in self.peers]
            read_list, _, _ = select.select(read, [], [], 1)

            # Receive from peers
            for socket in read_list:
                peer = self.get_peer_by_socket(socket)
                try:
                    msg = socket.recv(1024)
                except:
                    self.remove_peer(peer)
                    continue

                if len(msg) == 0:
                    self.remove_peer(peer)
                    continue

                peer.read_buffer += msg
                self.handle_message_received(peer)

    def start_connection_to_peers(self):
        for peer in self.peers:
            if not peer.has_handshaked:
                try:
                    peer.send_to_peer(peer.handshake)
                    interested = peer.build_interested()
                    peer.send_to_peer(interested)
                except:
                    self.remove_peer(peer)

    def add_peer(self, peer):
        self.peers.append(peer)

    def add_unchoked_peer(self, peer):
        self.unchoked_peers.append(peer)

    def remove_peer(self, peer):
        if peer in self.peers:
            try:
                peer.socket.close()
            except:
                pass

            self.peers.remove(peer)

        if peer in self.unchoked_peers:
            self.unchoked_peers.remove(peer)

        for rarestPiece in self.rarest_pieces.rarest_pieces:
            if peer in rarestPiece["peers"]:
                rarestPiece["peers"].remove(peer)

    def get_peer_by_socket(self, socket):
        for peer in self.peers:
            if socket == peer.socket:
                return peer

        raise ValueError("Peer not present in PeerList")

    def handle_peer_requests(self, piece, peer):
        piece_index, block_offset, block_length = piece
        block = self.pieces_manager.get_block(piece_index, block_offset, block_length)
        piece = peer.build_request(self, piece_index, block_offset, block)
        peer.send_to_peer(piece)

    @staticmethod
    def handle_message_received(peer):
        while len(peer.read_buffer) > 0:
            if peer.hasHandshaked is False:
                peer.check_handshake(peer.read_buffer)
                return

            message_length = utils.bytes_to_decimal(peer.read_buffer[0:4])

            # handle keep alive
            if peer.keep_alive(peer.read_buffer):
                return

            # len 0
            try:
                message_code = int(ord(peer.read_buffer[4:5]))
                payload = peer.read_buffer[5:4 + message_length]
            except Exception as e:
                logging.info(e)
                return

            # Message is not complete. Return
            if len(payload) < message_length - 1:
                return

            peer.read_buffer = peer.read_buffer[message_length + 4:]

            try:
                peer.id_to_function[message_code](payload)
            except Exception, e:
                logging.debug("Error id:", message_code, " ->", e)
                return

    @staticmethod
    def request_new_piece(peer, piece_index, offset, length):
        request = peer.build_request(piece_index, offset, length)
        peer.send_to_peer(request)
