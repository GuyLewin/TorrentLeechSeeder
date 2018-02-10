import logging
from bs4 import BeautifulSoup
import requests

# torrentleech_api
import torrentleechtorrent


TORRENTLEECH_BASE_URL = 'https://www.torrentleech.org'
ORDER_BY_LEECHERS_URL = "/torrents/browse/index/orderby/leechers/order/desc"
LOGIN_URL = "/user/account/login/"
PAGE_URL_SUFFIX = "/page/{page_num}"

INCORRECT_LOGIN_MAGIC = "Invalid Username"
CAPTCHA_MAGIC = "Maximum login attempts"


def _parse_torrents_from_url(session, url):
    search_url = TORRENTLEECH_BASE_URL + url
    response = session.get(search_url)

    torrents = list()

    if response.status_code == 200:
        parsed_response = BeautifulSoup(response.content, 'html.parser')
        table = parsed_response.find(id='torrenttable').find("tbody")
        for single_torrent_dom in table.find_all('tr'):
            url = single_torrent_dom.find('td', 'quickdownload').find('a')['href']
            size_str = single_torrent_dom.find_all('td')[4].get_text()
            seeders = int(single_torrent_dom.find('td', 'seeders').get_text())
            leechers = int(single_torrent_dom.find('td', 'leechers').get_text())

            logging.debug("Creating torrent (url={url}, size={size}, seeders={seeders}, leechers={leechers})".format(
                url=url, size=size_str, seeders=seeders, leechers=leechers
            ))
            torrents.append(torrentleechtorrent.TorrentLeechTorrent(url, size_str, seeders, leechers))

    return torrents


def get_top_scored_torrents(session, max_size_bytes, pages):
    torrents = list()
    for page_num in xrange(1, pages + 1):
        logging.info("Scraping page #{}".format(page_num))
        url = ORDER_BY_LEECHERS_URL
        if page_num > 1:
            url += PAGE_URL_SUFFIX.format(page_num=page_num)
        torrents += _parse_torrents_from_url(session, url)

    torrents_smaller_than_max_size = list()

    for single_torrent in torrents:
        if single_torrent.size_bytes < max_size_bytes:
            torrents_smaller_than_max_size.append(single_torrent)
            logging.debug("Torrent {torrent_url} is smaller than max_size".format(torrent_url=single_torrent.url))
        else:
            logging.debug("Torrent {torrent_url} is too big".format(torrent_url=single_torrent.url))

    # Sort them by their 'score' - preferring smaller torrents with more leechers and less seeders
    torrents_smaller_than_max_size.sort(key=lambda torrent_iter: torrent_iter.score, reverse=True)

    return torrents_smaller_than_max_size


def login(torrentleech_username, torrentleech_password):
    with requests.session() as session:
        login_result = session.post(TORRENTLEECH_BASE_URL + LOGIN_URL, data={
            'username': torrentleech_username,
            'password': torrentleech_password,
            'remember_me': 'on',
            'login': 'submit'
        })
        if INCORRECT_LOGIN_MAGIC in login_result.content:
            logging.error("Incorrect credentials. Quitting")
            return None
        elif CAPTCHA_MAGIC in login_result.content:
            logging.error("Too many incorrect login attempts. "
                          "Login via your browser and solve the captcha before retrying")
            return None
        return session
