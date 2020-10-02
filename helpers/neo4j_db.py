import logging

from decouple import config
from neo4j import TRUST_SYSTEM_CA_SIGNED_CERTIFICATES, GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from tqdm import tqdm

from helpers.schema import get_edge_properties


def neo4j_connect():
    """ Connection to Neo4j """

    driver_config = {
        "database": config("NEO4J_DB"),
        "encrypted": False,
        "trust": TRUST_SYSTEM_CA_SIGNED_CERTIFICATES,
        "user_agent": "osint",
        "max_connection_lifetime": 1000,
        "max_connection_pool_size": 100,
        "keep_alive": False,
        "max_transaction_retry_time": 10,
        "resolver": None,
    }

    try:
        driver = GraphDatabase.driver(
            config("NEO4J_URI"), auth=(config("NEO4J_USER"), config("NEO4J_PW")), **driver_config
        )
        driver.close()

        return driver

    except ServiceUnavailable as e:
        raise RuntimeError("Connection to Neo4j failed!") from e


def load_graph_into_db(nodes: dict, edges: dict):
    """
    Loading graph into database.
    Values of dictionaries are lists of dictionaries containing the node/edge properties.
    Edges have to have 'a' and 'b' as keys describing the two connected nodes.
    """

    # Neo4j connection
    neo4j = neo4j_connect()

    with neo4j.session() as session:
        # load nodes
        for label in nodes.keys():
            for node in tqdm(nodes[label], desc="Nodes " + label, total=len(nodes[label]), unit="nodes"):
                query = "MERGE(n:" + label + " {nodeId: $properties.nodeId}) ON CREATE SET n=$properties"
                session.run(query, properties=node)

        # load relationships
        edge_properties = get_edge_properties()
        for label in edges.keys():
            for edge in tqdm(edges[label], desc="Edges " + label, total=len(edges[label]), unit="edges"):
                if edge["a"] != edge["b"]:  # filter self-loops
                    query = (
                        "MATCH (a {nodeId: $a}), (b {nodeId: $b}) MERGE (a)-[r:"
                        + label
                        + " ]-(b) ON CREATE SET r=$properties"
                    )

                    if label == "CO_OCCURRENCE":
                        query += " ON MATCH SET r.count = r.count + 1"

                    session.run(query, **edge, properties=edge_properties[label])

    neo4j.close()
