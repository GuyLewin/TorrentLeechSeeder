import os
import pickle
import getpass
import logging
import argparse
import requests

import torrentleech_api.torrentleech_api

VERSION = "1.0"


def _dump_session(session, session_file_path):
    with open(session_file_path, "wb") as session_file:
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), session_file)


def _load_session(session_file_path):
    with open(session_file_path, "rb") as f:
        cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
        session = requests.session()
        session.cookies = cookies
        return session


def get_top_scored_torrents(torrentleech_username, torrentleech_password, session_file_path, max_size_bytes, pages):
    session = None
    if os.path.exists(session_file_path):
        try:
            session = _load_session(session_file_path)
        except Exception, e:
            logging.warning("Failed to load session. Using credentials")
            logging.debug("Exception: {}".format(str(e)))
    if session is None:
        # Load using credentials
        if torrentleech_username is None:
            torrentleech_username = raw_input("Username for TorrentLeech: ")
        if torrentleech_password is None:
            torrentleech_password = getpass.getpass("Password for {}: ".format(torrentleech_username))
        session = torrentleech_api.torrentleech_api.login(torrentleech_username, torrentleech_password)
        if session is None:
            return
        logging.info("Successful login! Saving session to {}".format(session_file_path))
        _dump_session(session, session_file_path)
    return torrentleech_api.torrentleech_api.get_top_scored_torrents(session, max_size_bytes, pages)


def main(argparse_args):
    if argparse_args.username is None and not os.path.exists(argparse_args.session):
        parser.error("You must specify -u/--username if session file doesn't exist")

    torrents = get_top_scored_torrents(
        argparse_args.username, argparse_args.password, argparse_args.session, argparse_args.max_size_bytes,
        argparse_args.pages
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TorrentLeech Seeder, version {}".format(VERSION))
    parser.add_argument("-u", "--username", dest="username", default=None,
                        help="Username for TorrentLeech website")
    parser.add_argument("-p", "--password", dest="password", default=None,
                        help="Password for TorrentLeech website. If not specified - script will ask for password")
    parser.add_argument("-s", "--session", dest="session", default=os.path.join(os.path.expanduser("~"), ".torrentleechseeder_session"),
                        help="Path to session file containing the cookies to TorrentLeech (will be generated "
                             "if first run)")
    parser.add_argument("-m", "--max-size", dest="max_size_bytes", type=int, default=53687091200,
                        help="Maximal size in bytes of a single torrent. Default: 50GB (%(default)d bytes)")
    parser.add_argument("--pages", dest="pages", type=int, default=3,
                        help="Number of pages to scrape TorrentLeech for torrents. Default: %(default)d")
    parser.add_argument("-d", "--download-dir", dest="download_dir",
                        help="Where downloaded torrents will be saved")
    args = parser.parse_args()

    if args.username is None and not os.path.exists(args.session):
        parser.error("You must specify -u/--username if session file doesn't exist")

    main(args)
