import struct
import random
import socket
import logging
import bencode
import requests
import threading
from urlparse import urlparse


class FuncThread(threading.Thread):
    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self)

    def run(self):
        self._target(*self._args)


class Tracker(object):
    def __init__(self, torrent, new_peers_queue):
        self.torrent = torrent
        self.threads_list = []
        self.new_peers_queue = new_peers_queue
        self.get_peers_from_trackers()

    def get_peers_from_trackers(self):
        for tracker in self.torrent.announce_list:
            if tracker[0][:4] == "http":
                t1 = FuncThread(self.scrape_http, self.torrent, tracker[0])
                self.threads_list.append(t1)
                t1.start()
            else:
                t2 = FuncThread(self.scrape_udp, self.torrent, tracker[0])
                self.threads_list.append(t2)
                t2.start()

        for t in self.threads_list:
            t.join()

    def scrape_http(self, torrent, tracker):
        params = {
            'info_hash': torrent.info_hash,
            'peer_id': torrent.peer_id,
            'uploaded': 0,
            'downloaded': 0,
            'left': torrent.total_length,
            'event': 'started'
        }
        try:
            tracker_response = requests.get(tracker, params=params, timeout=3)
            peers_list = bencode.bdecode(tracker_response.text)
            self.parse_tracker_response(peers_list['peers'])
        except:
            pass

    def parse_tracker_response(self, tracker_response):
        tracker_response_struct = "!IH"
        tracker_response_struct_size = struct.calcsize(tracker_response_struct)
        data = str(tracker_response)
        while len(data) > 0:
            raw_ip, port = struct.unpack(tracker_response_struct, data[:tracker_response_struct_size])
            ip = socket.inet_ntoa(raw_ip)
            self.new_peers_queue.put([ip, port])
            data = data[tracker_response_struct_size:]

    @staticmethod
    def make_connection_id_request():
        conn_id = struct.pack('>Q', 0x41727101980)
        action = struct.pack('>I', 0)
        trans_id = struct.pack('>I', random.randint(0, 100000))

        return conn_id + action + trans_id, trans_id, action

    @staticmethod
    def make_announce_input(info_hash, conn_id, peer_id):
        action = struct.pack('>I', 1)
        trans_id = struct.pack('>I', random.randint(0, 100000))

        downloaded = struct.pack('>Q', 0)
        left = struct.pack('>Q', 0)
        uploaded = struct.pack('>Q', 0)

        event = struct.pack('>I', 0)
        ip = struct.pack('>I', 0)
        key = struct.pack('>I', 0)
        num_want = struct.pack('>i', -1)
        port = struct.pack('>h', 8000)

        msg = (conn_id + action + trans_id + info_hash + peer_id + downloaded +
               left + uploaded + event + ip + key + num_want + port)

        return msg, trans_id, action

    def send_msg(self, conn, sock, msg, trans_id, action, size):
        sock.sendto(msg, conn)
        try:
            response = sock.recv(2048)
        except socket.timeout as err:
            logging.debug(err)
            return
            #logging.debug("Connecting again...")
            #return self.send_msg(conn, sock, msg, trans_id, action, size)
        if len(response) < size:
            logging.debug("Did not get full message. Connecting again...")
            return self.send_msg(conn, sock, msg, trans_id, action, size)

        if action != response[0:4] or trans_id != response[4:8]:
            logging.debug("Transaction or Action ID did not match. Trying again...")
            return self.send_msg(conn, sock, msg, trans_id, action, size)

        return response

    def scrape_udp(self, torrent, announce):
        try:
            parsed = urlparse(announce)
            ip = socket.gethostbyname(parsed.hostname)

            if ip == '127.0.0.1':
                return False
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            conn = (ip, parsed.port)
            msg, trans_id, action = Tracker.make_connection_id_request()
            response = self.send_msg(conn, sock, msg, trans_id, action, 16)
            if response is None:
                return ""

            conn_id = response[8:]
            msg, trans_id, action = Tracker.make_announce_input(torrent.info_hash, conn_id, torrent.peer_id)
            response = self.send_msg(conn, sock, msg, trans_id, action, 20)
            if response is None or len(response) == 0:
                return ""

            self.parse_tracker_response(response[20:])
        except:
            pass