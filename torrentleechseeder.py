import getpass
import argparse

import torrentleech_api.torrentleech_api

VERSION = "1.0"


def main(torrentleech_username, torrentleech_password):
    if torrentleech_password is None:
        torrentleech_password = getpass.getpass("Password for {}: ".format(torrentleech_username))
    torrentleech_api.torrentleech_api.get_top_leeched_torrents(torrentleech_username, torrentleech_password)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TorrentLeech Seeder, version {}".format(VERSION))
    parser.add_argument("username", metavar="username", action="store", help="Username for TorrentLeech website")
    parser.add_argument("-p", "--password", default=None, dest="password", action="store",
                        help="Password for TorrentLeech website. If not specified - script will ask for password")

    args = parser.parse_args()

    main(args.username, args.password)
