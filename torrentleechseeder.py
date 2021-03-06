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
from torrentleech_api.utils import size_str_to_float

VERSION = "1.0"

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# TODO: Support continuing downloaded torrents after restarting the script
# TODO: Kill aria2c + remove torrent data of old torrents

def _dump_session(session, session_file_path):
    with open(session_file_path, "wb") as session_file:
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), session_file)


def _load_session(session_file_path):
    with open(session_file_path, "rb") as f:
        cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
        session = requests.session()
        session.cookies = cookies
        return session


def _download_torrent_file(session, torrent_file_url):
    download_response = session.get(torrent_file_url)
    if download_response.status_code != 200:
        raise RuntimeError("Unable to download torrent from {0}, status code is {1}".format(
            torrent_file_url, download_response.status_code
        ))
    if "Access denied" in download_response.content:
        raise RuntimeError("Access denied while downloading torrent from {0}, status code is {1}".format(
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
            logging.debug("Exception: {0}".format(str(e)))
    if session is None:
        # Load using credentials
        if torrentleech_username is None:
            torrentleech_username = raw_input("Username for TorrentLeech: ")
        if torrentleech_password is None:
            torrentleech_password = getpass.getpass("Password for {0}: ".format(torrentleech_username))
        session = torrentleech_api.torrentleech_api.login(torrentleech_username, torrentleech_password)
        if session is None:
            return
        logging.info("Successful login! Saving session to {0}".format(session_file_path))
        _dump_session(session, session_file_path)
    return session, torrentleech_api.torrentleech_api.get_top_scored_torrents(session, max_size_bytes, pages)


def validate_args(parser, args):
    if args.username is None and not os.path.exists(args.session):
        parser.error("You must specify -u/--username if session file doesn't exist")

    if os.path.exists(args.download_dir) and not os.path.isdir(args.download_dir):
        parser.error("--download-dir must be a directory")

    try:
        size_str_to_float(args.max_size_bytes)
    except ValueError:
        parser.error("Invalid format for -m/--max-size. Format is (float)(unit) (e.g 50GB or 50.5MB)")

    try:
        size_str_to_float(args.download_dir_max_size)
    except ValueError:
        parser.error("Invalid format for --download-dir-max-size. Format is (float)(unit) (e.g 50GB or 50.5MB)")


def parse_arguments():
    parser = argparse.ArgumentParser(description="TorrentLeech Seeder, version {0}".format(VERSION))
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
    parser.add_argument("-m", "--max-size", dest="max_size_bytes", default="20GB",
                        help="Maximal size in bytes of a single torrent. Default: %(default)s")
    parser.add_argument("-i", "--interval", dest="interval", type=int, default=60 * 60 * 24,
                        help="Time in seconds to sleep between TorrentLeech scraping sessions. "
                             "Default: 1 day (%(default)d seconds)")
    parser.add_argument("--pages", dest="pages", type=int, default=5,
                        help="Number of pages to scrape TorrentLeech for torrents. Default: %(default)d")
    parser.add_argument("--download-dir-max-size", default="50GB",
                        dest="download_dir_max_size",
                        help="Maximal size all downloads will take altogether. "
                             "Default: %(default)s")
    parser.add_argument("--aria2c-path", default="/usr/bin/aria2c", dest="aria2c_path",
                        help="Path for the aria2c executable used to download and seed torrents. Default: %(default)s")

    args = parser.parse_args()
    validate_args(parser, args)
    return args


def main():
    args = parse_arguments()
    max_size_bytes = size_str_to_float(args.max_size_bytes)
    download_dir_max_size = size_str_to_float(args.download_dir_max_size)

    torrent_urls_already_downloaded = set()

    download_manager = aria2c_manager.Aria2cManager(args.download_dir, download_dir_max_size, args.aria2c_path)

    while download_manager.get_space_left(log=True) > 0:
        space_left = download_manager.get_space_left()
        session, torrents = get_top_scored_torrents(
            args.username, args.password, args.session,
            min(max_size_bytes, space_left), args.pages
        )

        for single_torrent in torrents:
            if single_torrent in torrent_urls_already_downloaded:
                continue
            logging.info("Downloading torrent {0}".format(single_torrent.url))
            try:
                torrent_file_path = _download_torrent_file(session, single_torrent.url)
            except RuntimeError, e:
                logging.error("Error while downloading torrent: {0}. Skipping".format(str(e)))
                continue
            logging.debug("Torrent file saved to {0}".format(torrent_file_path))
            aria2c_process = download_manager.download_torrent(torrent_file_path)
            if aria2c_process is None:
                break
            else:
                # Don't re-download
                torrent_urls_already_downloaded.add(single_torrent.url)

        logging.info("Sleeping for {0} seconds".format(args.interval))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
