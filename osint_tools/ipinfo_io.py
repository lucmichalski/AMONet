import json
from typing import Dict, List
from urllib.request import urlopen

from helpers.date_time import get_standardized_now
from helpers.geo import complete_location
from helpers.misc import clean_dict
from helpers.schema import check_schema, create_unique_id


def get_location_from_ip(ip: str) -> Dict[str, List[Dict]]:
    """ Get Location belonging to IP address. """

    # get location
    url = "http://ipinfo.io/" + ip + "/json"

    response = urlopen(url)
    data = json.load(response)

    # geo should not be NaN
    geo = data["loc"]

    if geo == geo:
        location = complete_location(data=geo, given="coordinates")

        # add basic information
        if location:
            location.update({"schemaVersion": 0.1, "timestamp": get_standardized_now()})
        else:
            return None

        # add unique id
        location_unique_id = create_unique_id(data=location, schema="Location")
        location["nodeId"] = location_unique_id

        # remove possible None and empty values
        location = clean_dict(d=location)

        # check schema
        if check_schema(data=location, schema="Location"):
            return {"Location": [location]}
        else:
            return None
