import os
import time
import pickle
import getpass
import logging
import tempfile
import argparse
import requests

import aria2c_manager
import torrentleech_api.torrentleech_api

VERSION = "1.0"

# Setup logger
logging.basicConfig(level=logging.DEBUG)


def _dump_session(session, session_file_path):
    with open(session_file_path, "wb") as session_file:
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), session_file)


def _load_session(session_file_path):
    with open(session_file_path, "rb") as f:
        cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
        session = requests.session()
        session.cookies = cookies
        return session


def _download_torrent_file(torrent_file_url):
    download_response = requests.get(torrent_file_url)
    if download_response.status_code != 200:
        raise ValueError("Unable to download torrent from {}, status code is {}".format(
            torrent_file_url, download_response.status_code
        ))
    torrent_file_save_path = tempfile.mktemp()
    with open(torrent_file_save_path, "wb") as torrent_file:
        torrent_file.write(download_response.content)
    return torrent_file_save_path


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

    torrent_urls_already_downloaded = set()

    download_manager = aria2c_manager.Aria2cManager(args.download_dir, args.download_dir_max_size, args.aria2c_path)

    while download_manager.get_space_left() > 0:
        torrents = get_top_scored_torrents(
            argparse_args.username, argparse_args.password, argparse_args.session,
            min(argparse_args.max_size_bytes, download_manager.get_space_left()), argparse_args.pages
        )

        for single_torrent in torrents:
            if single_torrent in torrent_urls_already_downloaded:
                continue
            download_manager.download_torrent(single_torrent.url)
            torrent_urls_already_downloaded.add(single_torrent.url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TorrentLeech Seeder, version {}".format(VERSION))
    parser.add_argument("-u", "--username", dest="username", default=None,
                        help="Username for TorrentLeech website")
    parser.add_argument("-p", "--password", dest="password", default=None,
                        help="Password for TorrentLeech website. If not specified - script will ask for password")
    parser.add_argument("-d", "--download-dir", dest="download_dir",
                        help="Where downloaded torrents will be saved")
    parser.add_argument("-s", "--session", dest="session",
                        default=os.path.join(os.path.expanduser("~"), ".torrentleechseeder_session"),
                        help="Path to session file containing the cookies to TorrentLeech (will be generated "
                             "if first run). Default: %(default)s")
    parser.add_argument("-m", "--max-size", dest="max_size_bytes", type=int, default=21474836480,
                        help="Maximal size in bytes of a single torrent. Default: 20GB (%(default)d bytes)")
    parser.add_argument("--pages", dest="pages", type=int, default=5,
                        help="Number of pages to scrape TorrentLeech for torrents. Default: %(default)d")
    parser.add_argument("--download-dir-max-size", default=53687091200, type=int, dest="download_dir_max_size",
                        help="Maximal size in bytes all downloads will take altogether. "
                             "Default: 50GB (%(default)d bytes)")
    parser.add_argument("--aria2c-path", default="/usr/bin/aria2c", dest="aria2c_path",
                        help="Path for the aria2c executable used to download and seed torrents. Default: %(default)s")
    args = parser.parse_args()

    if args.username is None and not os.path.exists(args.session):
        parser.error("You must specify -u/--username if session file doesn't exist")

    main(args)
