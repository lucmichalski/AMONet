import argparse
import logging
import os
import numpy as np

from pathlib import Path
from decouple import config
from tqdm import tqdm

from analytics.network_metrics import betweenness_centrality
from analytics.plotting import base_plotter, draw_world_map, table_plotter
from helpers.neo4j_db import load_graph_into_db, neo4j_connect
from helpers.nlp import ner
from helpers.schema import get_graph_model


# parser function to collect and pass on values from terminal
def parser():
    parser = argparse.ArgumentParser(description="Specify analytics process")

    parser.add_argument("--statistics", help="Calculate statistics.", action="store_true")  # default is false
    parser.add_argument("--most_used_keywords", help="Derive most used keywords.", action="store_true")
    parser.add_argument(
        "--world_map", help="Draw world map showing location contained in intelligence graph.", action="store_true"
    )
    parser.add_argument("--named_entity_recognition", help="Extract entities from text nodes.", action="store_true")
    parser.add_argument("--calculate_centrality", help="Calculate betweenness centrality.", action="store_true")

    args = parser.parse_args()

    return (
        args.statistics,
        args.most_used_keywords,
        args.world_map,
        args.named_entity_recognition,
        args.calculate_centrality,
    )


# pass on parser values
(
    statistics,
    most_used_keywords,
    world_map,
    named_entity_recognition,
    calculate_centrality,
) = parser()


if __name__ == "__main__":
    # logging
    logging.basicConfig(
        filename=os.path.join(config("LOG_DIR"), "analytics.log"),
        format=config("LOG_FORMAT"),
        level=config("LOG_LEVEL"),
        datefmt=config("LOG_DATEFMT"),
    )

    # Neo4j connection
    neo4j = neo4j_connect()

    ###############################################################################################
    # Statistics

    if statistics:
        with neo4j.session() as session:
            statistics = []

            # get statistics
            result = session.run("MATCH (n) RETURN COUNT(DISTINCT n) AS nodes_count")
            statistics.append(["Nodes", next(result.__iter__())["nodes_count"]])

            result = session.run("MATCH (a) -[r]- (b) RETURN COUNT(DISTINCT r) AS edges_count")
            statistics.append(["Edges", next(result.__iter__())["edges_count"]])

            graph_model = get_graph_model()
            nodes = graph_model["nodes"]
            edges = graph_model["edges"]

            for label in nodes:
                query = "MATCH (n:" + label + ") RETURN COUNT(DISTINCT n) AS nodes_count"
                result = session.run(query)
                statistics.append([(label + " nodes"), next(result.__iter__())["nodes_count"]])

            for label in edges:
                query = "MATCH (a) -[r:" + label + "]- (b) RETURN COUNT(DISTINCT r) AS edges_count"
                result = session.run(query)
                statistics.append([(label + " edges"), next(result.__iter__())["edges_count"]])

            # percentage of nodes
            nodes_percent = {
                s[0].split(" ")[0]: (s[1] / statistics[0][1]) * 100
                for s in statistics
                if s[0].split(" ")[0] in nodes and s[1] != 0
            }

            # plotting
            table_plotter(
                data=statistics,
                filename="statistics.png",
                title="Statistics",
                param_plot={"figsize": (9, 12)},
                param_ax={
                    "colLabels": ["$\\bf{Component}$", "$\\bf{Count}$"],
                    "cellLoc": "left",
                    "colLoc": "left",
                    "loc": "upper center",
                    "edges": "horizontal",
                    "colWidths": [0.5, 0.5],
                },
            )

            base_plotter(
                data_x=list(nodes_percent.values()),
                data_y=[],
                x_label="",
                y_label="",
                filename="nodes_distribution.png",
                title="Composition of Node Types",
                pie=True,
                param_plot={"figsize": (9, 9)},
                legend=list(nodes_percent.keys()),
            )

    ###############################################################################################
    # Most used keywords

    if most_used_keywords:

        with neo4j.session() as session:
            keywords = []

            query = "MATCH p=(k:Keyword)-[:INCLUSION]-(t:Text) WITH k, size(collect(p)) as degree WHERE degree > 1 RETURN k.keyword as keyword, degree ORDER BY degree DESC LIMIT 10"
            result = session.run(query)

            for r in result:
                keywords.append([r["keyword"], r["degree"]])

            # plotting
            base_plotter(
                data_x=np.array(keywords)[:, 1].astype(np.int),
                data_y=np.array(keywords)[:, 0],
                x_label="Degree",
                y_label="Keyword",
                filename="most_used_keywords.png",
                bar=True,
                horizontal=True,
                param_plot={"figsize": (10, 7)},
                param_ax={"facecolor": "cornflowerblue"},
            )

    ###############################################################################################
    # World map showing locations

    if world_map:
        # get geo coordinates of all locations in intelligence graph
        with neo4j.session() as session:
            latitude = []
            longitude = []

            query = "MATCH (n:Location) RETURN n.latitude as latitude, n.longitude as longitude"
            result = session.run(query)

            for r in result:
                latitude.append(r["latitude"])
                longitude.append(r["longitude"])

        draw_world_map(latitude, longitude)

    ###############################################################################################
    # Named entity recognition

    if named_entity_recognition:
        # init
        nodes_ner = {"Organization": []}
        edges_ner = {"INCLUSION": [], "CO_OCCURRENCE": []}
        # get text nodes
        with neo4j.session() as session:

            query = "MATCH (n:Text) RETURN n.text as text, n.nodeId as nodeId"
            result = session.run(query)

            texts = [(r["text"], r["nodeId"]) for r in result]

        # extract entities
        for t, t_node_id in texts:
            extracted_entities = ner(t)

            # store data
            if extracted_entities:
                # store node IDs of all derived entities
                node_ids = []
                n_i = 0

                # iterate over different entity types extracted from text
                for k, v in extracted_entities.items():
                    # add entity
                    nodes_ner[k].extend(v)

                    # iterate over different entities
                    for n in v:
                        # node ID
                        node_id = n["nodeId"]
                        node_ids.append(node_id)
                        # add INCLUSION relationship to original text node
                        edges_ner["INCLUSION"].append({"a": t_node_id, "b": node_id})

                        # add CO_OCCURRENCE relationship to other derived entities
                        for i in node_ids[:n_i]:
                            edges_ner["CO_OCCURRENCE"].append({"a": i, "b": node_id})

                        n_i += 1

        # store in intelligence graph
        load_graph_into_db(nodes=nodes_ner, edges=edges_ner)

    ###############################################################################################
    # Betweenness centrality

    if calculate_centrality:
        # calculate betweenness centrality and store as node property
        betweenness_centrality()

        # get top betweenness centralities for usernames and keywords
        with neo4j.session() as session:
            # username
            result_usernames = session.run(
                "MATCH (n:Username) RETURN n.betweennessCentrality AS betweennessCentrality, n.username AS username ORDER BY n.betweennessCentrality DESC LIMIT 10"
            )
            usernames_top_10 = [[r["username"], r["betweennessCentrality"]] for r in result_usernames]
            # keywords
            result_keywords = session.run(
                "MATCH (n:Keyword) RETURN n.betweennessCentrality AS betweennessCentrality, n.keyword AS keyword ORDER BY n.betweennessCentrality DESC LIMIT 10"
            )
            keywords_top_10 = [[r["keyword"], r["betweennessCentrality"]] for r in result_keywords]

        # plotting
        base_plotter(
            data_x=np.array(keywords_top_10)[:, 1].astype(np.float),
            data_y=np.array(keywords_top_10)[:, 0],
            x_label="Betweenness Centrality",
            y_label="Keyword",
            filename="keywords-centrality-top-10.png",
            bar=True,
            horizontal=True,
            param_plot={"figsize": (10, 7)},
            param_ax={"facecolor": "cornflowerblue"},
        )

        base_plotter(
            data_x=np.array(usernames_top_10)[:, 1].astype(np.float),
            data_y=np.array(usernames_top_10)[:, 0],
            x_label="Betweenness Centrality",
            y_label="Username",
            filename="usernames-centrality-top-10.png",
            bar=True,
            horizontal=True,
            param_plot={"figsize": (10, 7)},
            param_ax={"facecolor": "cornflowerblue"},
        )

    # close connection to Neo4j
    neo4j.close()
