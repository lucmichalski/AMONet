import argparse
import logging
import os
import pickle

from pathlib import Path
from decouple import config

from collect.twitter import store_twitter_data, twitter_lookup, twitter_search
from helpers.neo4j_db import neo4j_connect


# parser function to collect and pass on values from terminal
def parser():
    parser = argparse.ArgumentParser(description="Specify collection process")

    parser.add_argument("--keyword", help="Keyword used for search, e.g. '#OSINT'", type=str, default="")
    parser.add_argument(
        "--start_time", help="Start time for social media posts, e.g. '2015-12-20 20:30:15'", type=str, default=""
    )
    parser.add_argument(
        "--stop_time", help="Stop time for social media posts, e.g. '2017-11-10 10:15:15'", type=str, default=""
    )
    parser.add_argument("--platform", help="Platform of search, e.g. 'twitter' or 'facebook'", type=str, default="")

    args = parser.parse_args()

    return args.keyword, args.start_time, args.stop_time, args.platform


# pass on parser values
keyword, start_time, stop_time, platform = parser()

# deterministic hash values
os.environ["PYTHONHASHSEED"] = "0"


if __name__ == "__main__":
    # logging
    logging.basicConfig(
        filename=os.path.join(config("LOG_DIR"), "collect.log"),
        format=config("LOG_FORMAT"),
        level=config("LOG_LEVEL"),
        datefmt=config("LOG_DATEFMT"),
    )

    if platform == "twitter":

        # get Twitter data related to search
        twitter_data_path_posts = twitter_search(search_text=keyword, start=start_time, stop=stop_time)

        # store data
        store_twitter_data(data_path=twitter_data_path_posts, data_type="SocialMediaPost")

        """
        NOTE:
        As of 14. September 2020 Twint is no longer working for scraping user profiles. Future updates might fix this. 
        See the discussion on GitHub (https://github.com/twintproject/twint/issues/786).

        # get username nodes
        neo4j = neo4j_connect()

        with neo4j.session() as session:
            result = session.run("MATCH (n:Username) RETURN distinct n.username AS username")
            usernames = [r["username"] for r in result]

        neo4j.close()

        # get Twitter account information
        twitter_data_path_users = twitter_lookup(usernames=usernames)

        # store data
        store_twitter_data(data_path=twitter_data_path_users, data_type="UserAccount")
        """
