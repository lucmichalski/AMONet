import logging
import random
import string
import time
from functools import partial

from geopy.geocoders import Nominatim

from helpers.misc import clean_dict


def address_to_coordinates(address: str) -> str:
    """ Get geo coordinates from postal address. """

    try:
        geolocator = Nominatim(user_agent="osint_app")
        geocode = partial(geolocator.geocode, language="en")

        location = geolocator.geocode(address)

        result = location.raw["lat"] + ", " + location.raw["lon"]

        return result
    except Exception as e:
        logging.exception("Error in address_to_coordinates!")


def coordinates_to_address(coordinates: str) -> dict:
    """ Get postal address from geo coordinates, e.g., '51.1602, 10.4482'. """

    # convert coordinates to desired format
    coordinates = ", ".join(coordinates.split(","))

    try:
        geolocator = Nominatim(user_agent="osint_app")
        geocode = partial(geolocator.geocode, language="en")

        location = geolocator.reverse(coordinates, language="en")

        return location.raw
    except Exception as e:
        logging.exception("Error in coordinates_to_address!")


def geopy_to_schema(geopy_data: dict) -> dict:
    """ Converting Geopy raw location data into list of geo schema properties """

    # check if address data available
    try:
        address = geopy_data["address"]
    except KeyError as e:
        logging.exception("Exception occurred in geopy_to_schema: no address!")
        return [None] * 5

    # derive schema properties
    postalCode = address["postcode"] if "postcode" in address else None
    region = address["state"] if "state" in address else (address["county"] if "county" in address else None)
    street = (
        address["road"] + ", " + address["house_number"]
        if (("road" in address) and ("house_number" in address))
        else (address["road"] if "road" in address else None)
    )
    country = address["country_code"].upper() if "country_code" in address else None

    # city
    if "city" in address:
        locality = address["city"]
    elif "city_district" in address:
        locality = address["city_district"]
    elif "town" in address:
        locality = address["town"]
    elif "craft" in address:
        locality = address["craft"]
    elif "neighbourhood" in address:
        locality = address["neighbourhood"]
    else:
        locality = None

    return {
        "country": country,
        "locality": locality,
        "postalCode": postalCode,
        "region": region,
        "street": street,
        "completeAddress": geopy_data["display_name"],
    }


def complete_location(data: str, given: str = "address") -> dict:
    """ Completes location data. Can be addresses or geo coordinates, e.g. '52.509669, 13.376294'. """

    # get coordinates
    if given == "address":
        coordinates = address_to_coordinates(address=data)
        # sleep due to rate limit
        time.sleep(1)
    else:
        coordinates = data
        # convert coordinates to desired format
        coordinates = ", ".join(coordinates.split(","))

    if coordinates:
        try:
            # derive detailed address
            address = coordinates_to_address(coordinates=coordinates)
            location_schema = geopy_to_schema(geopy_data=address)

            # complete location data
            complete_location = {
                "latitude": float(coordinates.split(", ")[0]),
                "longitude": float(coordinates.split(", ")[1]),
            }
            complete_location.update(location_schema)

            # add raw data for reproducibility
            complete_location["rawData"] = str(data)

            # remove possible None and empty values
            complete_location = clean_dict(d=complete_location)

            return complete_location
        except Exception as e:
            logging.exception("Exception in complete_location! Data: %s" % data)
    else:
        return None
