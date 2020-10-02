from helpers.neo4j_db import neo4j_connect
from helpers.schema import get_edge_properties


def betweenness_centrality():
    """ Calculate betweenness centrality for ever node in network. """

    # Neo4j connection
    neo4j = neo4j_connect()

    # create in-memory graph
    with neo4j.session() as session:
        # create in memory graph
        session.run(
            "CALL gds.graph.create.cypher('betweennessGraph', 'MATCH (n) RETURN id(n) AS id', 'MATCH (n)-[]->(m) RETURN id(n) AS source, id(m) AS target')"
        )

        # calculate betweenness centrality
        r = session.run(
            "CALL gds.betweenness.write('betweennessGraph', { writeProperty: 'betweennessCentrality'}) YIELD minimumScore, maximumScore, createMillis, computeMillis, writeMillis"
        )

        # drop graph
        session.run("CALL gds.graph.drop('betweennessGraph')")


def louvain_community():
    """ Detect communities using the Louvain algorithm. """

    # Neo4j connection
    neo4j = neo4j_connect()

    # create in-memory graph
    with neo4j.session() as session:
        # check if graph already in memory
        graph_in_memory = session.run("CALL gds.graph.exists('communityGraphSeeded') YIELD exists")

        # otherwise create it
        if not graph_in_memory.single()["exists"]:
            session.run(
                "CALL gds.graph.create.cypher('communityGraph', 'MATCH (n) RETURN id(n) AS id', 'MATCH (n)-[r:CO_OCCURRENCE]->(m) RETURN id(n) AS source, id(m) AS target')"
            )

            # set community IDs
            session.run("CALL gds.louvain.write('communityGraph', { writeProperty: 'communityId'})")

            # create seeded graph for future queries
            session.run(
                "CALL gds.graph.create.cypher('communityGraphSeeded', 'MATCH (n) RETURN id(n) AS id, n.communityId as communityId', 'MATCH (n)-[r:CO_OCCURRENCE]->(m) RETURN id(n) AS source, id(m) AS target')"
            )

            # drop original graph
            session.run("CALL gds.graph.drop('communityGraph')")

        # set community IDs
        session.run(
            "CALL gds.louvain.write('communityGraphSeeded', { writeProperty: 'communityId', seedProperty: 'communityId'})"
        )
