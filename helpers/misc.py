import logging
import math
import os
import urllib.request
from datetime import datetime

import emoji
from decouple import config


def clean_dict(d: dict) -> dict:
    """ Clean dictionary of empty, None ... values. """

    # init
    result = dict()

    for k in d.keys():
        v = d[k]

        # check None
        if v is None:
            continue

        # check empty lists, dicts
        if not v:
            continue

        # check empty string (tabs, spaces included)
        if isinstance(v, str) and v.isspace():
            continue

        # check for NaN
        try:
            if math.isnan(float(v)):
                continue
        except Exception as e:
            pass

        # check for empty values in list
        if type(v) == list and type(v[0]) != dict:
            v = list(set(v))

        # add value to result dict
        result[k] = v

    # check if result is empty
    if not result:
        return None
    else:
        return result


def download_media(url: str) -> str:
    """
    Download file from url and save to data directory.
    return: path of downloaded file
    """

    try:
        file_path = os.path.join(config("DATA_DIR"), "media/" + url.split("/")[-1])
        urllib.request.urlretrieve(url, file_path)
        return file_path
    except Exception as e:
        logging.exception("Exception during fetching of media: %s!" % url)
        return None


def check_in_time_range(dt: str, start_datetime: str, stop_datetime: str) -> bool:
    """
    Checks if dt is in time range from start_datetime to stop_datetime.
    Format should be %Y-%m-%dT%H:%M:%SZ, e.g. 2020-01-02T07:51:14Z.
    """

    # convert to timestamp
    start_datetime = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    stop_datetime = datetime.strptime(stop_datetime, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    if start_datetime <= dt <= stop_datetime:
        return True
    else:
        return False


def remove_emojis(s: str) -> str:
    """ Function to remove Emojis from string. """

    return emoji.get_emoji_regexp().sub(r"", s)
