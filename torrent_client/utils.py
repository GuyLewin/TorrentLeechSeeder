import hashlib


def bytes_to_decimal(header_bytes):
    size = 0
    power = len(header_bytes) - 1

    for ch in header_bytes:
        size += int(ord(ch)) * 256 ** power
        power -= 1
    return size


def sha1_hash(string):
    """
    Return 20-byte sha1 hash of string.
    """
    return hashlib.sha1(string).digest()