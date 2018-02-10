"""
Static utilities for implementing TorrentLeech API
"""


def size_str_to_float(size_str):
    size_float = float(size_str.split(" ")[0])

    if size_str.endswith("KB"):
        return size_float * 1024
    elif size_str.endswith("MB"):
        return size_float * 1024 * 1024
    elif size_str.endswith("GB"):
        return size_float * 1024 * 1024 * 1024
    elif size_str.endswith("TB"):
        return size_float * 1024 * 1024 * 1024 * 1024
    else:
        raise ValueError("Unsupported size string: {}".format(size_str))
