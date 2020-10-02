import json
import logging
from os.path import dirname, join
from typing import Dict, List

from decouple import config
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import ValidationError

from helpers.date_time import get_standardized_now
from helpers.hash import create_hash


def get_primary_keys(schema: str) -> List[str]:
    """ Return primary key for given schema. """

    # read file
    with open(config("PRIMARY_KEYS_FILE"), "r") as primary_keys_file:
        primary_keys = json.load(primary_keys_file)

    return primary_keys[schema]


def get_schema(schema: str) -> dict:
    """ Get specified schema. """

    schema_path = join(config("SCHEMA_DIR_PATH"), schema + ".json")
    with open(schema_path, "r") as schema_file:
        data_schema = json.load(schema_file)

    return data_schema


def get_properties(schema: str, required: bool = False) -> List[str]:
    """ Return properties of given schema. """

    # get schema
    data_schema = get_schema(schema=schema)

    # return either required or all properties
    if required:
        return Draft7Validator(data_schema).schema["required"]
    else:
        return list(Draft7Validator(data_schema).schema["properties"].keys())


def check_schema(data: dict, schema: str) -> bool:
    """ Checks whether the given data matches the schema. """

    # get schemas
    base_schema = get_schema(schema="Base")
    data_schema = get_schema(schema=schema)

    # resolve references
    resolver = RefResolver.from_schema(base_schema)

    # check if schema is valid
    Draft7Validator.check_schema(data_schema)

    # validate data
    validator = Draft7Validator(data_schema, resolver=resolver)

    try:
        validator.validate(data)
        return True
    except ValidationError:
        logging.exception("Exception occurred in check_schema: Invalid schema!")
        return False


def create_unique_id(data: dict, schema: str) -> str:
    """ Create unique id for given subject. """

    # get primary keys
    pks = get_primary_keys(schema=schema)

    # create unique id if primary key values are available
    try:
        pks_values = list({k: str(data[k]).lower() for k in pks}.values())

        unique_id = schema + "-".join(pks_values)
        unique_id = create_hash(s=unique_id)

        return unique_id

    except KeyError:
        return None


def get_edge_properties() -> dict:
    """ Get default properties of edges. """

    # basic information of all nodes
    basic_info = {"timestamp": get_standardized_now(), "schemaVersion": 0.1}

    # basic information of all relationships
    inclusion = basic_info.copy()
    co_occurrence = basic_info.copy()
    co_occurrence.update(
        {"loopViolation": False, "cyclesCount": 0, "similarity": 0, "weight": 0, "count": 1, "verified": False}
    )

    if check_schema(data=co_occurrence, schema="CO_OCCURRENCE") and check_schema(data=inclusion, schema="INCLUSION"):
        pass
    else:
        raise RuntimeError("Wrong schema of relationship in data_model.py!")

    edge_properties = {"INCLUSION": inclusion, "CO_OCCURRENCE": co_occurrence}

    return edge_properties


def get_graph_model() -> Dict[str, List[str]]:
    """ Get types of nodes and edges. """

    # data model
    atoms = [
        "Username",
        "Organization",
        "Keyword",
        "Person",
        "Domain",
        "Location",
        "IpAddress",
        "Email",
        "Phone",
        "HashValue",
    ]
    organisms = ["SocialMediaPost", "UserAccount"]
    molecules = ["Media", "Text"]

    nodes = organisms + molecules + atoms
    edges = ["INCLUSION", "CO_OCCURRENCE"]

    return {"nodes": nodes, "edges": edges, "atoms": atoms, "molecules": molecules, "organisms": organisms}
