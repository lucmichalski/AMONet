import json
from typing import Dict, List

from decouple import config

from helpers.misc import clean_dict
from helpers.neo4j_db import load_graph_into_db, neo4j_connect
from helpers.schema import get_primary_keys
from osint_tools.ipinfo_io import get_location_from_ip
from osint_tools.network_socket import get_ip_from_domain

# map tool names to functions
tool2function = {"networkSocket": get_ip_from_domain, "ipinfoIo": get_location_from_ip}


def enrich_node(node: dict) -> List[Dict]:
    """ Gather OSINT data and enrich given node. """

    # check input
    with open(config("OSINT_MATRIX")) as f:
        osint_matrix = json.load(f)
        osint_entities = list(osint_matrix.keys())

    entity_type = node["label"]

    assert entity_type in osint_entities, "OSINT enrichment not supported for given entity_type: %s!" % entity_type

    # init
    nodes_enrichment = {
        "SocialMediaPost": [],
        "Username": [],
        "Person": [],
        "Location": [],
        "Text": [],
        "Media": [],
        "UserAccount": [],
        "Domain": [],
        "Keyword": [],
        "Email": [],
        "IpAddress": [],
        "Organization": [],
        "Phone": [],
        "HashValue": [],
    }

    edges_enrichment = {"CO_OCCURRENCE": []}

    # get primary keys of entity node
    pks = get_primary_keys(entity_type)
    entity_value = [node[pk] for pk in pks]

    # get OSINT tools
    entity_tools = list(set(sum(list(osint_matrix[entity_type].values()), [])))

    # get OSINT data
    for t in entity_tools:
        # get data from OSINT tool
        d = tool2function[t](*entity_value)
        # store data
        if d:
            # store node IDs of all derived entities
            node_ids = []
            n_i = 0

            # iterate over different entity types received from OSINT tool
            for k, v in d.items():
                # add entities
                nodes_enrichment[k].extend(v)

                # iterate over different entities
                for n in v:
                    # store node ID
                    node_id = n["nodeId"]
                    node_ids.append(node_id)
                    # add CO_OCCURRENCE relationship to original node
                    edges_enrichment["CO_OCCURRENCE"].append({"a": node["nodeId"], "b": node_id})

                    # add CO_OCCURRENCE relationship to other derived entities
                    for i in node_ids[:n_i]:
                        edges_enrichment["CO_OCCURRENCE"].append({"a": i, "b": node_id})

                    n_i += 1

    # store in intelligence graph
    load_graph_into_db(nodes=nodes_enrichment, edges=edges_enrichment)

    # added nodes
    added_nodes = []
    for k, v in nodes_enrichment.items():
        [n.update({"label": k}) for n in v]
        added_nodes.extend(v)

    return added_nodes
