import socket
from typing import Dict, List

from helpers.date_time import get_standardized_now
from helpers.schema import check_schema, create_unique_id


def get_ip_from_domain(domain: str) -> Dict[str, List[Dict]]:
    """ Get IP address belonging to domain. """

    # get IP
    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        return None

    # IP address object
    ip_address = {"ip": ip, "version": 4, "timestamp": get_standardized_now(), "schemaVersion": 0.1}

    # add node ID
    ip_address_unique_id = create_unique_id(data=ip_address, schema="IpAddress")
    ip_address["nodeId"] = ip_address_unique_id

    # check schema
    if check_schema(data=ip_address, schema="IpAddress"):
        return {"IpAddress": [ip_address]}
    else:
        return None
