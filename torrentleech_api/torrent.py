"""
Model to contain information about a single TorrentLeech torrent
"""
import utils


class Torrent(object):
    def __init__(self, url, size_str, seeders, leechers):
        self.url = url
        self.size_str = size_str
        self.size_bytes = utils.size_str_to_float(self.size_str)
        self.seeders = seeders
        self.leechers = leechers
        self.score = self.leechers / self.size_bytes / max(1, self.seeders)

    def __repr__(self):
        return "{0} | size: {0} | seeders: {0} | leechers: {0} | score: {0}".format(
            self.url.split("/")[-1], self.size_str, self.seeders, self.leechers, self.score
        )
