import ast
import logging
import os

import pandas as pd
import twint
from decouple import config
from tqdm import tqdm

from helpers.data_static import ALEXA1M
from helpers.date_time import get_standardized_now, standardize_date_time
from helpers.extractor import extract_media_info, extract_name, extract_urls
from helpers.geo import complete_location
from helpers.hash import create_hash, get_checksum
from helpers.misc import clean_dict, download_media
from helpers.neo4j_db import load_graph_into_db
from helpers.schema import check_schema, create_unique_id, get_primary_keys, get_properties


def twitter_lookup(usernames: str) -> str:
    """
    Collecting data of Twitter user accounts.
    return: Path of file containing collected data.
    """

    # configure; see http://github.com/twintproject/twint/wiki/Configuration
    c = twint.Config()

    c.Hide_output = True
    c.Store_csv = True

    data_description = " ".join(usernames)
    data_description_hash = create_hash(s=data_description)
    data_path = config("DATA_DIR") + "/collect/twint_" + data_description_hash + ".csv"

    c.Output = data_path

    twint_user_properties = [
        "id",
        "name",
        "username",
        "bio",
        "location",
        "url",
        "join_date",
        "join_time",
        "tweets",
        "following",
        "followers",
        "likes",
        "media",
        "private",
        "verified",
        "profile_image_url",
        "background_image",
    ]

    c.Custom["users"] = twint_user_properties

    for user in tqdm(usernames, total=len(usernames), unit="accounts"):
        # set username
        c.Username = user

        # running search
        twint.run.Lookup(c)

    return data_path


def twitter_search(search_text: str, start: str = "", stop: str = "") -> str:
    """
    Collecting Twitter data related to search.

    start/stop: Datetime for social media posts, e.g. 2015-12-20 20:30:15 (%Y-%m-%d %H:%M:%S)
    return: Path of file containing collected data.
    """

    # configure; see http://github.com/twintproject/twint/wiki/Configuration
    c = twint.Config()

    c.Search = search_text
    c.Store_csv = True
    c.Since = start
    c.Until = stop
    c.Hide_output = True

    data_description = " ".join(search_text)
    data_description_hash = create_hash(s=data_description)
    data_path = config("DATA_DIR") + "/collect/twitter_" + data_description_hash + ".csv"
    c.Output = data_path

    resume_path = config("DATA_DIR") + "/collect/twitter_" + "resume_" + data_description_hash + ".csv"
    c.Resume = resume_path

    twint_tweet_properties = [
        "id",
        "created_at",
        "user_id",
        "username",
        "name",
        "tweet",
        "mentions",
        "urls",
        "photos",
        "replies_count",
        "retweets_count",
        "likes_count",
        "hashtags",
        "cashtags",
        "link",
        "retweet",
        "geo",
        "source",
        "retweet_date",
    ]
    c.Custom["tweet"] = twint_tweet_properties

    # running search
    twint.run.Search(c)

    return data_path


def store_twitter_data(data_path: str, data_type: str = "SocialMediaPost"):
    """
    Store collected Twitter data in Neo4j database.
    data_type: type of collected data (SocialMediaPosting or UserAccount)
    """

    # check input
    organisms = ["SocialMediaPost", "UserAccount"]
    assert data_type in organisms, "data_type should be 'SocialMediaPost' or 'UserAccount'!"

    # init
    nodes = {
        "SocialMediaPost": [],
        "Username": [],
        "Person": [],
        "Location": [],
        "Text": [],
        "Media": [],
        "UserAccount": [],
        "Domain": [],
        "Keyword": [],
        "HashValue": [],
    }
    edges = {"INCLUSION": [], "CO_OCCURRENCE": []}

    # read data
    data = pd.read_csv(data_path, sep=",", header=0)

    # drop duplicates
    data.drop_duplicates(subset=["id"], keep="first", inplace=True)

    # basic information of all nodes/relationships
    basic_info = {"timestamp": get_standardized_now(), "schemaVersion": 0.1}

    # extract nodes/links for every entry
    records = data.to_dict(orient="records")

    if data_type == "SocialMediaPost":

        for x in tqdm(records, desc="SocialMediaPosts", total=len(records), unit="records"):

            ###############################################################################################
            # SocialMediaPost

            # information given in data
            social_media_post = {
                "platform": "twitter",
                "id": str(x["id"]),
                "url": x["link"],
                "shared": x["retweet"],
                "likesCount": x["likes_count"],
                "repliesCount": x["replies_count"],
                "sharesCount": x["retweets_count"],
                "datePublished": standardize_date_time(date_time=(int(x["created_at"] / 1000)), timestamp=True),
            }

            """
            Unfortunately, given the information Twint extracts, it can not be determined whether the posting
            is a reply or the original one.
            """

            if x["retweet"]:
                social_media_post["type"] = "share"

            # add basic information
            social_media_post.update(basic_info)

            # add unique id
            social_media_post_unique_id = create_unique_id(data=social_media_post, schema="SocialMediaPost")
            social_media_post["nodeId"] = social_media_post_unique_id

            # remove possible None and empty values
            social_media_post = clean_dict(d=social_media_post)

            # check schema
            if check_schema(data=social_media_post, schema="SocialMediaPost"):
                # add node to graph
                nodes["SocialMediaPost"].append(social_media_post)
            else:
                continue

            ###############################################################################################
            # Username

            # information given in data
            username = {"username": x["username"]}

            # add basic information
            username.update(basic_info)

            # add unique id
            username_unique_id = create_unique_id(data=username, schema="Username")
            username["nodeId"] = username_unique_id

            # remove possible None and empty values
            username = clean_dict(d=username)

            # check schema
            if check_schema(data=username, schema="Username"):
                # add node to graph
                nodes["Username"].append(username)
                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": social_media_post_unique_id, "b": username_unique_id})

            ###############################################################################################
            # Person

            # information given
            person = extract_name(s=x["name"])

            # add basic information
            person.update(basic_info)

            # add unique id
            person_unique_id = create_unique_id(data=person, schema="Person")
            person["nodeId"] = person_unique_id

            # remove possible None and empty values
            person = clean_dict(d=person)

            # check schema
            if check_schema(data=person, schema="Person"):
                # add node to graph
                nodes["Person"].append(person)
                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": social_media_post_unique_id, "b": person_unique_id})
                # add CO_OCCURRENCE relationship
                edges["CO_OCCURRENCE"].append({"a": username_unique_id, "b": person_unique_id})

            ###############################################################################################
            # Location

            # geo should not be NaN
            geo = x["geo"]
            if geo == geo:
                location = complete_location(data=geo, given="coordinates")
                # add basic information
                location.update(basic_info)

                # add unique id
                location_unique_id = create_unique_id(data=location, schema="Location")
                location["nodeId"] = location_unique_id

                # remove possible None and empty values
                location = clean_dict(d=location)

                # check schema
                if check_schema(data=location, schema="Location"):
                    # add node to graph
                    nodes["Location"].append(location)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": social_media_post_unique_id, "b": location_unique_id})
                    # add CO_OCCURRENCE relationships
                    edges["CO_OCCURRENCE"].append({"a": username_unique_id, "b": location_unique_id})
                    edges["CO_OCCURRENCE"].append({"a": person_unique_id, "b": location_unique_id})

            ###############################################################################################
            # Media (Photos)

            media_urls = list(set([n.strip() for n in ast.literal_eval(x["photos"])]))

            for url in media_urls:
                # download
                file_path = download_media(url=url)
                if file_path is None:
                    continue

                # information given in data
                media = {"url": url, "type": "image", **extract_media_info(s=url)}

                # add basic information
                media.update(basic_info)

                # add unique id
                media_unique_id = create_unique_id(data=media, schema="Media")
                media["nodeId"] = media_unique_id

                # remove possible None and empty values
                media = clean_dict(d=media)

                # check schema
                if check_schema(data=media, schema="Media"):
                    # add node to graph
                    nodes["Media"].append(media)

                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": social_media_post_unique_id, "b": media_unique_id})

                    # add hash value
                    hash_value = {"hashValue": get_checksum(file=file_path)}

                    # add basic information
                    hash_value.update(basic_info)

                    # add unique id
                    hash_value_unique_id = create_unique_id(data=hash_value, schema="HashValue")
                    hash_value["nodeId"] = hash_value_unique_id

                    # remove possible None and empty values
                    hash_value = clean_dict(d=hash_value)

                    # check schema
                    if check_schema(data=hash_value, schema="HashValue"):
                        # add node to graph
                        nodes["HashValue"].append(hash_value)
                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": media_unique_id, "b": hash_value_unique_id})

            ###############################################################################################
            # Text

            # information given in data
            keywords = [n.strip() for n in ast.literal_eval(x["hashtags"])] + [
                n.strip() for n in ast.literal_eval(x["cashtags"])
            ]
            urls_in_text = [n.strip() for n in ast.literal_eval(x["urls"])]
            text = {"text": x["tweet"]}

            # add basic information
            text.update(basic_info)

            # add unique id
            text_unique_id = create_unique_id(data=text, schema="Text")
            text["nodeId"] = text_unique_id

            # remove possible None and empty values
            text = clean_dict(d=text)

            # check schema
            if check_schema(data=text, schema="Text"):
                # add node to graph
                nodes["Text"].append(text)
                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": social_media_post_unique_id, "b": text_unique_id})

            ###############################################################################################
            # Keywords

            keywords = list(set([n.strip() for n in ast.literal_eval(x["hashtags"])]))

            # store node IDs of all username mentions
            node_ids = []

            for h_i, h in enumerate(keywords):
                # information given in data
                keyword = {"keyword": h}

                # add basic information
                keyword.update(basic_info)

                # add unique id
                keyword_unique_id = create_unique_id(data=keyword, schema="Keyword")
                keyword["nodeId"] = keyword_unique_id

                node_ids.append(keyword_unique_id)

                # remove possible None and empty values
                keyword = clean_dict(d=keyword)

                # check schema
                if check_schema(data=keyword, schema="Keyword"):
                    # add node to graph
                    nodes["Keyword"].append(keyword)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": text_unique_id, "b": keyword_unique_id})
                    # add CO_OCCURRENCE relationship
                    for i in node_ids[:h_i]:
                        edges["CO_OCCURRENCE"].append({"a": i, "b": keyword_unique_id})

            ###############################################################################################
            # Domains

            # store node IDs of all username mentions
            node_ids = []

            for u_i, u in enumerate(list(set(urls_in_text))):
                # extract URL information
                extracted_url_info = extract_urls(u)

                try:
                    extracted_url_info = extracted_url_info[next(iter(extracted_url_info))]
                except StopIteration:
                    continue

                if not extracted_url_info:
                    continue

                # do not consider large webpages
                domain = extracted_url_info["domain"]

                if domain in ALEXA1M:
                    continue

                # information given in data
                domain = {"domain": domain}

                # add basic information
                domain.update(basic_info)

                # add unique id
                domain_unique_id = create_unique_id(data=domain, schema="Domain")
                domain["nodeId"] = domain_unique_id

                node_ids.append(domain_unique_id)

                # remove possible None and empty values
                domain = clean_dict(d=domain)

                # check schema
                if check_schema(data=domain, schema="Domain"):
                    # add node to graph
                    nodes["Domain"].append(domain)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": text_unique_id, "b": domain_unique_id})
                    # add CO_OCCURRENCE relationship
                    for i in node_ids[:u_i]:
                        edges["CO_OCCURRENCE"].append({"a": i, "b": domain_unique_id})

            ###############################################################################################
            # Usernames (Mentions)

            mentions = list(set([n.strip() for n in ast.literal_eval(x["mentions"])]))

            # store node IDs of all username mentions
            node_ids = []

            for m_i, m in enumerate(mentions):
                # information given in data
                username = {"username": m}

                # add basic information
                username.update(basic_info)

                # add unique id
                username_unique_id = create_unique_id(data=username, schema="Username")
                username["nodeId"] = username_unique_id

                node_ids.append(username_unique_id)

                # remove possible None and empty values
                username = clean_dict(d=username)

                # check schema
                if check_schema(data=username, schema="Username"):
                    # add node to graph
                    nodes["Username"].append(username)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": text_unique_id, "b": username_unique_id})
                    # add CO_OCCURRENCE relationship
                    for i in node_ids[:m_i]:
                        edges["CO_OCCURRENCE"].append({"a": i, "b": username_unique_id})

    if data_type == "UserAccount":

        for x in tqdm(records, desc="UserAccounts", total=len(records), unit="records"):

            ###############################################################################################
            # UserAccount

            # information given in data
            user_account = {
                "private": bool(x["private"]),
                "verifiedByPlatform": bool(x["verified"]),
                "followersCount": x["followers"],
                "followingCount": x["following"],
                "dateTimeJoined": standardize_date_time(
                    date_time=(x["join_date"] + " " + x["join_time"]), format="%d %b %Y %I:%M %p"
                ),
                "mediaCount": x["media"],
                "postingsCount": x["tweets"],
                "platform": "twitter",
                "id": str(x["id"]),
                "url": ("https:/twitter.com/" + x["username"]),
                "likesCount": x["likes"],
            }

            # add basic information
            user_account.update(basic_info)

            # add unique id
            user_account_unique_id = create_unique_id(data=user_account, schema="UserAccount")
            user_account["nodeId"] = user_account_unique_id

            # remove possible None and empty values
            user_account = clean_dict(d=user_account)

            # check schema
            if check_schema(data=user_account, schema="UserAccount"):
                # add node to graph
                nodes["UserAccount"].append(user_account)
            else:
                continue

            ###############################################################################################
            # Username

            """
            The username has already been added to the graph during storage of collected Tweets.
            The unique ID of the node is calculated for later use.
            An INCLUSION edge is added between the usename and the user account.
            """

            # unique id
            username_unique_id = create_unique_id(data={"username": x["username"]}, schema="Username")

            # add INCLUSION relationship
            edges["INCLUSION"].append({"a": user_account_unique_id, "b": username_unique_id})

            ###############################################################################################
            # Person

            """
            The person has already been added to the graph during storage of collected Tweets.
            The unique ID of the node is calculated for later use.
            An INCLUSION edge is added between the person and the user account.
            """

            # unique id
            person_unique_id = create_unique_id(data=extract_name(s=x["name"]), schema="Person")

            # add INCLUSION relationship
            edges["INCLUSION"].append({"a": user_account_unique_id, "b": person_unique_id})

            ###############################################################################################
            # Text

            text = x["bio"]

            # text should not be NaN
            if text == text:
                # information given in data
                text = {"text": text}

                # add basic information
                text.update(basic_info)

                # add unique id
                text_unique_id = create_unique_id(data=text, schema="Text")
                text["nodeId"] = text_unique_id

                # remove possible None and empty values
                text = clean_dict(d=text)

                # check schema
                if check_schema(data=text, schema="Text"):
                    # add node to graph
                    nodes["Text"].append(text)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": user_account_unique_id, "b": text_unique_id})

            ###############################################################################################
            # Domains

            text = x["bio"]

            if text == text:
                # extract urls form bio
                extracted_urls = extract_urls(text)

                # store node IDs of all username mentions
                node_ids = []

                for u_i, u in enumerate(list(set(extracted_urls.keys()))):
                    # URL information
                    url_info = extracted_urls[u]

                    if not url_info:
                        continue

                    # do not consider large webpages
                    domain = url_info["domain"]

                    if domain in ALEXA1M:
                        continue

                    # information given in data
                    domain = {"domain": domain}

                    # add basic information
                    domain.update(basic_info)

                    # add unique id
                    domain_unique_id = create_unique_id(data=domain, schema="Domain")
                    domain["nodeId"] = domain_unique_id

                    node_ids.append(domain_unique_id)

                    # remove possible None and empty values
                    domain = clean_dict(d=domain)

                    # check schema
                    if check_schema(data=domain, schema="Domain"):
                        # add node to graph
                        nodes["Domain"].append(domain)
                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": text_unique_id, "b": domain_unique_id})
                        # add CO_OCCURRENCE relationship
                        for i in node_ids[:u_i]:
                            edges["CO_OCCURRENCE"].append({"a": i, "b": domain_unique_id})

            ###############################################################################################
            # Location

            # location should be given
            location = x["location"]

            # location should not be NaN
            if location == location:
                location = complete_location(data=location, given="address")

                # only continue if location could be retrieved
                if location:
                    # add basic information
                    location.update(basic_info)

                    # add unique id
                    location_unique_id = create_unique_id(data=location, schema="Location")
                    location["nodeId"] = location_unique_id

                    # remove possible None and empty values
                    location = clean_dict(d=location)

                    # check schema
                    if check_schema(data=location, schema="Location"):
                        # add node to graph
                        nodes["Location"].append(location)
                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": user_account_unique_id, "b": location_unique_id})
                        # add CO_OCCURRENCE relationships
                        edges["CO_OCCURRENCE"].append({"a": username_unique_id, "b": location_unique_id})
                        edges["CO_OCCURRENCE"].append({"a": person_unique_id, "b": location_unique_id})

            ###############################################################################################
            # Media (profile image and profile background image)

            media_urls = list(set([x["profile_image_url"], x["background_image"]]))

            for i, url in enumerate(media_urls):
                # URL should not be NaN
                if url == url:
                    # download
                    file_path = download_media(url=url)
                    if file_path is None:
                        continue

                    # information given in data
                    media = {"url": url, "type": "image", **extract_media_info(s=url)}

                    # add type of image properties
                    if i == 0:
                        media["profileImage"] = True
                    if i == 1:
                        media["profileBackgroundImage"] = True

                    # add basic information
                    media.update(basic_info)

                    # add unique id
                    media_unique_id = create_unique_id(data=media, schema="Media")
                    media["nodeId"] = media_unique_id

                    # remove possible None and empty values
                    media = clean_dict(d=media)

                    # check schema
                    if check_schema(data=media, schema="Media"):
                        # add node to graph
                        nodes["Media"].append(media)

                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": user_account_unique_id, "b": media_unique_id})

                        # add hash value
                        hash_value = {"hashValue": get_checksum(file=file_path)}

                        # add basic information
                        hash_value.update(basic_info)

                        # add unique id
                        hash_value_unique_id = create_unique_id(data=hash_value, schema="HashValue")
                        hash_value["nodeId"] = hash_value_unique_id

                        # remove possible None and empty values
                        hash_value = clean_dict(d=hash_value)

                        # check schema
                        if check_schema(data=hash_value, schema="HashValue"):
                            # add node to graph
                            nodes["HashValue"].append(hash_value)
                            # add INCLUSION relationship
                            edges["INCLUSION"].append({"a": media_unique_id, "b": hash_value_unique_id})

    # load data into database
    load_graph_into_db(nodes=nodes, edges=edges)
