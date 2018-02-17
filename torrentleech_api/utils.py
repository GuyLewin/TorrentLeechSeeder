"""
Static utilities for implementing TorrentLeech API
"""
import re

SIZE_STR_PATTERN = r"(\d+(?:\.\d*)?)([KMGT]?B)"


def size_str_to_float(size_str):
    # Support "50GB" and "50 GB"
    size_str = size_str.replace(" ", "").strip()
    matches = re.match(SIZE_STR_PATTERN, size_str)
    if matches is None or len(matches.groups()) != 2:
        raise ValueError("Unsupported size string: {0}".format(size_str))
    size_float = float(matches.groups()[0])
    unit = matches.groups()[1]

    if unit == "KB":
        return size_float * 1024
    elif unit == "MB":
        return size_float * 1024 * 1024
    elif unit == "GB":
        return size_float * 1024 * 1024 * 1024
    elif unit == "TB":
        return size_float * 1024 * 1024 * 1024 * 1024
    else:
        raise ValueError("Unsupported size string: {0}".format(size_str))


def size_float_to_str(size_float):
    size_in_unit = size_float
    unit = "B"
    if size_float > 1024:
        size_in_unit /= 1024
        unit = "KB"
    if size_float > 1024 * 1024:
        size_in_unit /= 1024
        unit = "MB"
    if size_float > 1024 * 1024 * 1024:
        size_in_unit /= 1024
        unit = "GB"
    if size_float > 1024 * 1024 * 1024 * 1024:
        size_in_unit /= 1024
        unit = "TB"
    return "{0:.2f}{1}".format(size_in_unit, unit)
