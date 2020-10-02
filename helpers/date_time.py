import datetime


def standardize_date_time(date_time: str, timestamp: bool = False, format: str = "") -> str:
    """ Standardize date time to be in line with ISO 8601 """

    if timestamp:
        dt = datetime.datetime.fromtimestamp(int(date_time))
        iso_dt = dt.replace(microsecond=0).isoformat()
    else:
        dt = datetime.datetime.strptime(date_time, format)
        iso_dt = dt.replace(microsecond=0).isoformat()

    return str(iso_dt) + "Z"


def get_standardized_now() -> str:
    """ Standardized date time of 'now' in line with ISO 8601 """

    return str(datetime.datetime.now().replace(microsecond=0).isoformat()) + "Z"
