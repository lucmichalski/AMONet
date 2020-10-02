# AMONet: Leveraging Entity Co-occurrences for Open Source Intelligence

> by the [Database Systems Research Group](http://dbs.ifi.uni-heidelberg.de) @Heidelberg University

## Setup

Tested with Python 3.7.5.

### 1. Python Environment

- Clone repository into preferred directory

  ```
  git clone https://github.com/jomazi/AMONet.git
  ```

- Create virtual environment

  ```
  cd AMONet/
  virtualenv venv
  source venv/bin/activate
  ```

- Install `helpers` as package

  ```
  pip install -e .
  ```

- Install required packages

  ```
  pip install -r requirements.txt
  ```

- Install `spaCy` model:
  ```
  python -m spacy download de_core_news_sm
  ```

### 2. Neo4j via Docker

**Docker Installation**

To be able to get the Docker service up and running install [Docker](http://docs.docker.com/install) and [Docker Compose](http://docs.docker.com/compose).

Also take care of the [post installation steps](http://docs.docker.com/install/linux/linux-postinstall).

**Neo4j Setup**

Run the following command to setup Neo4j via Docker. Do not forget to specify the user password.

```
docker run \
    --name neo4j \
    -p7473:7473 -p7474:7474 -p7687:7687 \
    -d \
    --env NEO4J_AUTH=neo4j/password \
    --env NEO4J_dbms_memory_pagecache_size=1G \
    --env=NEO4J_dbms_memory_heap_max__size=2G \
    --env NEO4J_dbms_security_procedures_unrestricted=gds.* \
    --env NEO4J_dbms_security_procedures_whitelist=gds.* \
    --volume=${PWD}/neo4j/plugins:/var/lib/neo4j/plugins \
    --restart unless-stopped \
    neo4j:4.1.1
```

For more details see [How-To: Run Neo4j in Docker](http://neo4j.com/developer/docker-run-neo4j) and the official [documentation](http://neo4j.com/docs/operations-manual/current/docker).

**Ports**

- 7474 for HTTP
- 7473 for HTTPS
- 7687 for Bolt

**Helpful Commands**

| Description       | Command                                                   |
| ----------------- | --------------------------------------------------------- |
| stop container    | docker stop neo4j                                         |
| start container   | docker start neo4j                                        |
| destroy container | docker rm neo4j                                           |
| Cypher shell      | docker exec -it neo4j cypher-shell -u neo4j -p `password` |

**Initialize Database**

Copy `init.cypher` file into Docker container:

```
docker cp ${PWD}/neo4j/init.cypher neo4j:/var/lib/neo4j/init.cypher
```

Execute Cypher query:

```
docker exec neo4j bash -c "cat /var/lib/neo4j/init.cypher | cypher-shell -u neo4j -p password"
```

**Database Population**

Run the following commands from the root of this project. Do not forget to adjust the `.example.env` file and rename it to `.env`:

1. Use case: Social media intelligence

```
python main_collect.py --keyword="#lobbyregister" --start_time="2020-06-01 00:00:00" --stop_time="2020-09-15 23:59:59" --platform="twitter"
python main_analytics.py --named_entity_recognition
```

2. Use case: Location inference

```
python main_osint_enrichment.py --order=2 --entity_type="Domain"
```

**Evaluation: Cross-network user tracking**

Due to privacy reasons the data is being kept private.

```
python ./evaluation/cross-network.py --collect
python ./evaluation/cross-network.py --sample
python ./evaluation/cross-network.py --load

# evaluation
python ./evaluation/cross-network.py --evaluation
```
