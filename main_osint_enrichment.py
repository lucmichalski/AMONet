import argparse
import logging
import os

from decouple import config

from helpers.misc import clean_dict
from helpers.neo4j_db import neo4j_connect
from helpers.osint_enrichment import enrich_node
from helpers.schema import get_graph_model


# parser function to collect and pass on values from terminal
def parser():
    parser = argparse.ArgumentParser(description="Specify OSINT enrichment process.")

    parser.add_argument("--order", help="Number of OSINT expansions.", default=1, type=int)
    parser.add_argument("--entity_type", help="Enrich only given entity type.", type=str, default="")

    args = parser.parse_args()

    return args.order, args.entity_type


# pass on parser values
order, entity_type = parser()


if __name__ == "__main__":
    # logging
    logging.basicConfig(
        filename=os.path.join(config("LOG_DIR"), "enrichment.log"),
        format=config("LOG_FORMAT"),
        level=config("LOG_LEVEL"),
        datefmt=config("LOG_DATEFMT"),
    )

    ###############################################################################################
    # Get nodes that should be enriched

    # Neo4j
    neo4j = neo4j_connect()

    with neo4j.session() as session:
        query = (
            "MATCH (n) WITH n, LABELS(n) AS labels WHERE labels[0] in "
            + str(get_graph_model()["atoms"])
            + " RETURN PROPERTIES(n) AS properties, labels[0] AS label"
        )

        result = session.run(query)

        nodes2enrich = []

        for r in result:
            node = r["properties"]
            node["label"] = r["label"]

            nodes2enrich.append(node)

    # filter nodes
    if entity_type:
        nodes2enrich = [n for n in nodes2enrich if n["label"] == entity_type]

    # close connection
    neo4j.close()

    print("Got leaf nodes!")

    ###############################################################################################
    # Enrich Data

    # repeat enrichment process
    for i in range(order):

        # store nodes that have been enriched and will be expanded further
        nodes2enrich_updated = []

        for n in nodes2enrich:
            added_nodes = enrich_node(node=n)
            nodes2enrich_updated.extend(added_nodes)

        nodes2enrich = nodes2enrich_updated

    print("Enriched data!")
