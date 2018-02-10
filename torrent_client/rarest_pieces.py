class RarestPieces(object):
    def __init__(self, pieces_manager):
        self.pieces_manager = pieces_manager
        self.rarest_pieces = []

        for piece_number in range(self.pieces_manager.number_of_pieces):
            peers_by_piece_index = {"piece_id": piece_number, "numberOfPeers": 0, "peers": []}
            self.rarest_pieces.append(peers_by_piece_index)

    def peers_bitfield(self, bitfield=None, peer=None, piece_index=None):
        if len(self.rarest_pieces) == 0:
            raise ValueError("no more pieces")

        # Piece complete
        try:
            if piece_index is not None:
                self.rarest_pieces.__delitem__(piece_index)
        except:
            pass

        # Peer's bitfield updated
        else:
            for i in range(len(self.rarest_pieces)):
                if bitfield[i] == 1 and peer not in self.rarest_pieces[i]["peers"]:
                    self.rarest_pieces[i]["peers"].append(peer)
                    self.rarest_pieces[i]["numberOfPeers"] = len(self.rarest_pieces[i]["peers"])

    def get_sorted_pieces(self):
        return sorted(self.rarest_pieces, key=lambda piece: piece['number_of_peers'])
