import os
import time
import pandas as pd
import numpy as np
import argparse
import phonenumbers
import logging

from decouple import config
from tqdm import tqdm

from analytics.plotting import table_plotter
from helpers.date_time import get_standardized_now
from helpers.mongodb import mongodb_connect
from helpers.schema import check_schema, create_unique_id
from helpers.extractor import extract_facebook_id, extract_name, extract_urls
from helpers.misc import clean_dict
from helpers.neo4j_db import load_graph_into_db, neo4j_connect
from helpers.geo import complete_location
from osint_tools.vk import get_vk_id
from osint_tools.twitter import get_twitter_user
from osint_tools.instaloader import get_instagram_id


# parser function to collect and pass on values from terminal
def parser():
    parser = argparse.ArgumentParser(description="Specify evaluation process.")

    parser.add_argument("--sample", help="Load sample of linked user accounts.", action="store_true")
    parser.add_argument("--collect", help="Collect information on linked Twitter accounts.", action="store_true")
    parser.add_argument("--load", help="Load collected information into database.", action="store_true")
    parser.add_argument("--evaluation", help="Evaluate gain in information.", action="store_true")  # default is false

    args = parser.parse_args()

    return args.sample, args.evaluation, args.collect, args.load


# pass on parser values
sample, evaluation, collect, load = parser()


def cross_network_user_sample():
    """
    Extract sample of linked accounts of VK users and process to be used
    in AMONet framework.
    """

    # get data
    # client and database to connect to MongoDB
    mongo_client, mongo_db = mongodb_connect()

    # get account related information
    related_information = list(
        mongo_db["osint_vk_accounts"].find(
            {
                "$or": [
                    {"instagram": {"$exists": "true"}},
                    {"facebook": {"$exists": "true"}},
                    {"twitter": {"$exists": "true"}},
                ]
            },
            {
                "instagram": 1,
                "facebook": 1,
                "twitter": 1,
                "screen_name": 1,
                "_id": 0,
            },
            skip=40,
            limit=10,
        )
    )

    # create dataframe from information
    df = pd.DataFrame(related_information)
    df = df.rename(columns={"screen_name": "vk", "site": "website"})

    # drop users with no connected account, even no vk screen name
    df.dropna(how="all", inplace=True)

    # store data in network
    # init
    nodes = {
        "Username": [],
        "UserAccount": [],
    }
    edges = {"INCLUSION": [], "CO_OCCURRENCE": []}

    # basic information of all nodes/relationships
    basic_info = {"timestamp": get_standardized_now(), "schemaVersion": 0.1}

    for index, x in tqdm(df.iterrows(), desc="VK accounts", total=len(df), unit="records"):

        #######################################################################
        # VK

        if x["vk"]:
            # information given in data
            vk_user_account = {"platform": "vk", "id": get_vk_id(username=x["vk"]), "url": ("https:/vk.com/" + x["vk"])}
            time.sleep(0.3)

            # add basic information
            vk_user_account.update(basic_info)

            # add unique id
            vk_user_account_unique_id = create_unique_id(data=vk_user_account, schema="UserAccount")
            vk_user_account["nodeId"] = vk_user_account_unique_id

            # remove possible None and empty values
            vk_user_account = clean_dict(d=vk_user_account)

            # check schema
            if check_schema(data=vk_user_account, schema="UserAccount"):
                # add node to graph
                nodes["UserAccount"].append(vk_user_account)

                # add username
                vk_username = {"username": x["vk"]}
                vk_username.update(basic_info)
                vk_username_unique_id = ""  # reset
                vk_username_unique_id = create_unique_id(data=vk_username, schema="Username")
                vk_username["nodeId"] = vk_username_unique_id

                if check_schema(data=vk_username, schema="Username"):
                    # add node to graph
                    nodes["Username"].append(vk_username)
                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_username_unique_id})
                else:
                    vk_username_unique_id = ""  # reset
            else:
                vk_user_account_unique_id = ""  # reset
                continue
        else:
            # reset
            vk_user_account_unique_id = ""
            vk_username_unique_id = ""

        #######################################################################
        # Twitter

        try:
            # information given in data
            twitter_user_account = {
                "platform": "twitter",
                "id": get_twitter_user(username=x["twitter"]).id_str,
                "url": ("https:/twitter.com/" + x["twitter"]),
            }

            # add basic information
            twitter_user_account.update(basic_info)

            # add unique id
            twitter_user_account_unique_id = create_unique_id(data=twitter_user_account, schema="UserAccount")
            twitter_user_account["nodeId"] = twitter_user_account_unique_id

            # remove possible None and empty values
            twitter_user_account = clean_dict(d=twitter_user_account)

            # check schema
            if check_schema(data=twitter_user_account, schema="UserAccount"):
                # add node to graph
                nodes["UserAccount"].append(twitter_user_account)

                # add username
                twitter_username = {"username": x["twitter"]}
                twitter_username.update(basic_info)
                twitter_username_unique_id = create_unique_id(data=twitter_username, schema="Username")
                twitter_username["nodeId"] = twitter_username_unique_id

                if check_schema(data=twitter_username, schema="Username"):
                    # add node to graph
                    nodes["Username"].append(twitter_username)
                    # add INCLUSION relationships
                    edges["INCLUSION"].append({"a": twitter_user_account_unique_id, "b": twitter_username_unique_id})
                    edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": twitter_username_unique_id})
                    # add CO_OCCURRENCE relationship
                    edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": twitter_username_unique_id})
                else:
                    twitter_user_username_unique_id = ""  # reset
            else:
                twitter_user_account_unique_id = ""  # reset
        except Exception as e:
            # reset
            twitter_user_account_unique_id = ""
            twitter_username_unique_id = ""

        #######################################################################
        # Facebook

        if x["facebook"] and (type(x["facebook"]) is str):
            # get Facebook ID
            facebook_id = extract_facebook_id(s=x["facebook"])

            if facebook_id:
                # information given in data
                facebook_user_account = {
                    "platform": "facebook",
                    "id": facebook_id,
                    "url": ("https:/facebook.com/" + facebook_id),
                }

                # add basic information
                facebook_user_account.update(basic_info)

                # add unique id
                facebook_user_account_unique_id = ""  # reset
                facebook_user_account_unique_id = create_unique_id(data=facebook_user_account, schema="UserAccount")
                facebook_user_account["nodeId"] = facebook_user_account_unique_id

                # remove possible None and empty values
                facebook_user_account = clean_dict(d=facebook_user_account)

                # check schema
                if check_schema(data=facebook_user_account, schema="UserAccount"):
                    # add node to graph
                    nodes["UserAccount"].append(facebook_user_account)

                    # add username
                    facebook_username = {"username": facebook_id}
                    facebook_username.update(basic_info)
                    facebook_username_unique_id = ""  # reset
                    facebook_username_unique_id = create_unique_id(data=facebook_username, schema="Username")
                    facebook_username["nodeId"] = facebook_username_unique_id

                    if check_schema(data=facebook_username, schema="Username"):
                        # add node to graph
                        nodes["Username"].append(facebook_username)
                        # add INCLUSION relationship
                        edges["INCLUSION"].append(
                            {"a": facebook_user_account_unique_id, "b": facebook_username_unique_id}
                        )
                        edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": facebook_username_unique_id})
                        # add CO_OCCURRENCE relationship
                        edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": facebook_username_unique_id})
                        if twitter_user_account_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": twitter_username_unique_id, "b": facebook_username_unique_id}
                            )
                    else:
                        facebook_username_unique_id = ""  # reset
                else:
                    facebook_user_account_unique_id = ""  # reset
        else:
            # reset
            facebook_user_account_unique_id = ""
            facebook_username_unique_id = ""

        #######################################################################
        # Instagram

        if x["instagram"] and (type(x["instagram"]) is str):
            # get Instagram ID
            instagram_id = get_instagram_id(username=x["instagram"])

            if instagram_id:
                # information given in data
                instagram_user_account = {
                    "platform": "instagram",
                    "id": instagram_id,
                    "url": ("https:/instagram.com/" + instagram_id),
                }

                # add basic information
                instagram_user_account.update(basic_info)

                # add unique id
                instagram_user_account_unique_id = ""  # reset
                instagram_user_account_unique_id = create_unique_id(data=instagram_user_account, schema="UserAccount")
                instagram_user_account["nodeId"] = instagram_user_account_unique_id

                # remove possible None and empty values
                instagram_user_account = clean_dict(d=instagram_user_account)

                # check schema
                if check_schema(data=instagram_user_account, schema="UserAccount"):
                    # add node to graph
                    nodes["UserAccount"].append(instagram_user_account)

                    # add username
                    instagram_username = {"username": x["instagram"]}
                    instagram_username.update(basic_info)
                    instagram_username_unique_id = ""  # reset
                    instagram_username_unique_id = create_unique_id(data=instagram_username, schema="Username")
                    instagram_username["nodeId"] = instagram_username_unique_id

                    if check_schema(data=instagram_username, schema="Username"):
                        # add node to graph
                        nodes["Username"].append(instagram_username)
                        # add INCLUSION relationship
                        edges["INCLUSION"].append(
                            {"a": instagram_user_account_unique_id, "b": instagram_username_unique_id}
                        )
                        edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": instagram_username_unique_id})
                        # add CO_OCCURRENCE relationship
                        edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": instagram_username_unique_id})
                        if twitter_username_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": twitter_username_unique_id, "b": instagram_username_unique_id}
                            )
                        if facebook_user_account_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": facebook_username_unique_id, "b": instagram_username_unique_id}
                            )
                    else:
                        instagram_username_unique_id = ""  # reset
                else:
                    instagram_user_account_unique_id = ""  # reset
        else:
            # reset
            instagram_user_account_unique_id = ""
            instagram_username_unique_id = ""

    # load data into database
    load_graph_into_db(nodes=nodes, edges=edges)


def collect_connected_twitter_accounts():
    """
    Collect information of Twitter accounts linked to
    VK profiles.
    """

    # get data
    # client and database to connect to MongoDB
    mongo_client, mongo_db = mongodb_connect()

    # get account related information
    related_information = list(
        mongo_db["osint_vk_accounts"].find(
            {
                "twitter": {"$exists": "true"},
            },
            {
                "twitter": 1,
                "_id": 1,
            },
        )
    )

    for x in tqdm(related_information, desc="VK accounts", total=len(related_information), unit="records"):
        # get Twitter profile
        twitter_user = get_twitter_user(username=x["twitter"])
        time.sleep(0.3)

        # store in MongoDB
        if twitter_user:
            query = {"_id": x["_id"]}
            values = {"$set": {"twitter_profile": twitter_user._json}}
            mongo_db["osint_vk_accounts"].update_one(query, values)


def load_in_db():
    """
    Load collected information into database according
    AMONet model.
    """

    # get data
    # client and database to connect to MongoDB
    mongo_client, mongo_db = mongodb_connect()

    # get account related information
    related_information = list(
        mongo_db["osint_vk_accounts"].find(
            {
                "twitter_profile": {"$exists": "true"},
            },
            {
                "twitter_profile": 1,
                "screen_name": 1,
                "city": 1,
                "country": 1,
                "first_name": 1,
                "last_name": 1,
                "university_name": 1,
                "home_phone": 1,
                "instagram": 1,
                "site": 1,
                "skype": 1,
                "twitter": 1,
                "facebook": 1,
                "_id": 0,
            },
        )
    )

    # basic information of all nodes/relationships
    basic_info = {"timestamp": get_standardized_now(), "schemaVersion": 0.1}

    for x in tqdm(related_information, desc="accounts", total=len(related_information), unit="records"):

        # store data in network
        # init
        nodes = {
            "Username": [],
            "UserAccount": [],
            "Location": [],
            "Person": [],
            "Organization": [],
            "Phone": [],
            "Domain": [],
        }
        edges = {"INCLUSION": [], "CO_OCCURRENCE": []}

        #######################################################################
        # VK account/username

        # information given in data
        vk_user_account = {
            "platform": "vk",
            "id": get_vk_id(username=x["screen_name"]),
            "url": ("https:/vk.com/" + x["screen_name"]),
        }
        time.sleep(0.3)

        # add basic information
        vk_user_account.update(basic_info)

        # add unique id
        vk_user_account_unique_id = create_unique_id(data=vk_user_account, schema="UserAccount")
        vk_user_account["nodeId"] = vk_user_account_unique_id

        # remove possible None and empty values
        vk_user_account = clean_dict(d=vk_user_account)

        # check schema
        if check_schema(data=vk_user_account, schema="UserAccount"):
            # add node to graph
            nodes["UserAccount"].append(vk_user_account)

            # add username
            vk_username = {"username": x["screen_name"]}
            vk_username.update(basic_info)
            vk_username_unique_id = ""  # reset
            vk_username_unique_id = create_unique_id(data=vk_username, schema="Username")
            vk_username["nodeId"] = vk_username_unique_id

            if check_schema(data=vk_username, schema="Username"):
                # add node to graph
                nodes["Username"].append(vk_username)
                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_username_unique_id})
            else:
                vk_username_unique_id = ""  # reset
        else:
            vk_user_account_unique_id = ""  # reset
            continue

        #######################################################################
        # VK location

        try:
            # information given in data
            vk_location = complete_location(data=x["city"]["title"] + ", " + x["country"]["title"], given="address")
            time.sleep(0.3)

            # add basic information
            vk_location.update(basic_info)

            # add unique id
            vk_location_unique_id = create_unique_id(data=vk_location, schema="Location")
            vk_location["nodeId"] = vk_location_unique_id

            # remove possible None and empty values
            vk_location = clean_dict(d=vk_location)

            # check schema
            if check_schema(data=vk_location, schema="Location"):
                # add node to graph
                nodes["Location"].append(vk_location)

                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_location_unique_id})

                # add CO_OCCURRENCE relationship
                if vk_username_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_location_unique_id})
        except Exception as e:
            # reset
            vk_location_unique_id = ""

        #######################################################################
        # VK person

        try:
            # information given in data
            vk_person = extract_name(s=x["first_name"] + " " + x["last_name"])

            # add basic information
            vk_person.update(basic_info)

            # add unique id
            vk_person_unique_id = create_unique_id(data=vk_person, schema="Person")
            vk_person["nodeId"] = vk_person_unique_id

            # remove possible None and empty values
            vk_person = clean_dict(d=vk_person)

            # check schema
            if check_schema(data=vk_person, schema="Person"):
                # add node to graph
                nodes["Person"].append(vk_person)

                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_person_unique_id})

                # add CO_OCCURRENCE relationships
                if vk_username_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_person_unique_id})
                if vk_location_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_location_unique_id, "b": vk_person_unique_id})
        except KeyError:
            # reset
            vk_person_unique_id = ""

        #######################################################################
        # VK organization

        try:
            # information given in data
            vk_organization = {
                "name": x["university_name"],
                "rawData": x["university_name"],
                "description": "university",
            }

            # add basic information
            vk_organization.update(basic_info)

            # add unique id
            vk_organization_unique_id = create_unique_id(data=vk_organization, schema="Organization")
            vk_organization["nodeId"] = vk_organization_unique_id

            # remove possible None and empty values
            vk_organization = clean_dict(d=vk_organization)

            # check schema
            if check_schema(data=vk_organization, schema="Organization"):
                # add node to graph
                nodes["Organization"].append(vk_organization)

                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_organization_unique_id})

                # add CO_OCCURRENCE relationships
                if vk_username_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_organization_unique_id})
                if vk_location_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_location_unique_id, "b": vk_organization_unique_id})
                if vk_person_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_person_unique_id, "b": vk_organization_unique_id})
        except KeyError:
            # reset
            vk_organization_unique_id = ""

        #######################################################################
        # VK phone

        try:
            # check if valid phone number
            phone = phonenumbers.parse(x["home_phone"], None)

            if phonenumbers.is_valid_number(phone):
                # information given in data
                vk_phone = {"phone": phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)}

                # add basic information
                vk_phone.update(basic_info)

                # add unique id
                vk_phone_unique_id = create_unique_id(data=vk_phone, schema="Phone")
                vk_phone["nodeId"] = vk_phone_unique_id

                # remove possible None and empty values
                vk_phone = clean_dict(d=vk_phone)

                # check schema
                if check_schema(data=vk_phone, schema="Phone"):
                    # add node to graph
                    nodes["Phone"].append(vk_phone)

                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_phone_unique_id})

                    # add CO_OCCURRENCE relationships
                    if vk_username_unique_id:
                        edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_phone_unique_id})
                    if vk_location_unique_id:
                        edges["CO_OCCURRENCE"].append({"a": vk_location_unique_id, "b": vk_phone_unique_id})
                    if vk_person_unique_id:
                        edges["CO_OCCURRENCE"].append({"a": vk_person_unique_id, "b": vk_phone_unique_id})
                    if vk_organization_unique_id:
                        edges["CO_OCCURRENCE"].append({"a": vk_organization_unique_id, "b": vk_phone_unique_id})
        except Exception as e:
            # reset
            vk_phone_unique_id = ""

        #######################################################################
        # VK domains

        if x["site"]:
            # information given in data
            extracted_domains = extract_urls(s=x["site"])

            if len(extracted_domains.items()) > 0:
                domains_unique_ids = []

                for d in extracted_domains.values():
                    vk_domain = {"domain": d["domain"]}

                    # add basic information
                    vk_domain.update(basic_info)

                    # add unique id
                    vk_domain_unique_id = create_unique_id(data=vk_domain, schema="Domain")
                    vk_domain["nodeId"] = vk_domain_unique_id

                    # remove possible None and empty values
                    vk_domain = clean_dict(d=vk_domain)

                    # check schema
                    if check_schema(data=vk_domain, schema="Domain"):
                        # add node to graph
                        nodes["Domain"].append(vk_domain)

                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_domain_unique_id})

                        # add CO_OCCURRENCE relationships
                        if vk_username_unique_id:
                            edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_domain_unique_id})
                        if vk_location_unique_id:
                            edges["CO_OCCURRENCE"].append({"a": vk_location_unique_id, "b": vk_domain_unique_id})
                        if vk_person_unique_id:
                            edges["CO_OCCURRENCE"].append({"a": vk_person_unique_id, "b": vk_domain_unique_id})
                        if vk_organization_unique_id:
                            edges["CO_OCCURRENCE"].append({"a": vk_organization_unique_id, "b": vk_domain_unique_id})
                        if vk_phone_unique_id:
                            edges["CO_OCCURRENCE"].append({"a": vk_phone_unique_id, "b": vk_domain_unique_id})
                        for i in domains_unique_ids:
                            edges["CO_OCCURRENCE"].append({"a": i, "b": vk_domain_unique_id})

                        domains_unique_ids.append(vk_domain_unique_id)
            else:
                # reset
                domains_unique_ids = []
        else:
            # reset
            domains_unique_ids = []

        #######################################################################
        # VK additional usernames

        additional_usernames = [x["twitter"]]
        additional_usernames_unique_ids = []

        try:
            additional_usernames.append(x["facebook"])
        except KeyError:
            pass
        try:
            additional_usernames.append(x["instagram"])
        except KeyError:
            pass
        try:
            additional_usernames.append(x["skype"])
        except KeyError:
            pass

        # add additional usernames as nodes
        for u in additional_usernames:
            # information given in data
            vk_additional_username = {"username": u}

            # add basic information
            vk_additional_username.update(basic_info)

            # add unique id
            vk_additional_username_unique_id = create_unique_id(data=vk_additional_username, schema="Username")
            vk_additional_username["nodeId"] = vk_additional_username_unique_id

            # remove possible None and empty values
            vk_additional_username = clean_dict(d=vk_additional_username)

            # check schema
            if check_schema(data=vk_additional_username, schema="Username"):
                # add node to graph
                nodes["Username"].append(vk_additional_username)

                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": vk_user_account_unique_id, "b": vk_additional_username_unique_id})

                # add CO_OCCURRENCE relationships
                if vk_username_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_username_unique_id, "b": vk_additional_username_unique_id})
                if vk_location_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_location_unique_id, "b": vk_additional_username_unique_id})
                if vk_person_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_person_unique_id, "b": vk_additional_username_unique_id})
                if vk_organization_unique_id:
                    edges["CO_OCCURRENCE"].append(
                        {"a": vk_organization_unique_id, "b": vk_additional_username_unique_id}
                    )
                if vk_phone_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": vk_phone_unique_id, "b": vk_additional_username_unique_id})
                for i in domains_unique_ids:
                    edges["CO_OCCURRENCE"].append({"a": i, "b": vk_additional_username_unique_id})
                for i in additional_usernames_unique_ids:
                    edges["CO_OCCURRENCE"].append({"a": i, "b": vk_additional_username_unique_id})

                additional_usernames_unique_ids.append(vk_additional_username_unique_id)

        #######################################################################
        # Twitter account/username

        # information given in data
        twitter_user_account = {
            "platform": "twitter",
            "id": x["twitter_profile"]["id_str"],
            "url": ("https:/twitter.com/" + x["twitter_profile"]["id_str"]),
        }

        # add basic information
        twitter_user_account.update(basic_info)

        # add unique id
        twitter_user_account_unique_id = create_unique_id(data=twitter_user_account, schema="UserAccount")
        twitter_user_account["nodeId"] = twitter_user_account_unique_id

        # remove possible None and empty values
        twitter_user_account = clean_dict(d=twitter_user_account)

        # check schema
        if check_schema(data=twitter_user_account, schema="UserAccount"):
            # add node to graph
            nodes["UserAccount"].append(twitter_user_account)

            # add username
            twitter_username = {"username": x["twitter_profile"]["screen_name"]}
            twitter_username.update(basic_info)
            twitter_username_unique_id = ""  # reset
            twitter_username_unique_id = create_unique_id(data=twitter_username, schema="Username")
            twitter_username["nodeId"] = twitter_username_unique_id

            if check_schema(data=twitter_username, schema="Username"):
                # add node to graph
                nodes["Username"].append(twitter_username)
                # add INCLUSION relationships
                edges["INCLUSION"].append({"a": twitter_user_account_unique_id, "b": twitter_username_unique_id})
            else:
                twitter_username_unique_id = ""  # reset
        else:
            twitter_user_account_unique_id = ""  # reset
            continue

        #######################################################################
        # Twitter location

        if x["twitter_profile"]["location"]:
            # information given in data
            twitter_location = complete_location(data=x["twitter_profile"]["location"], given="address")
            time.sleep(0.3)

            if twitter_location:
                # add basic information
                twitter_location.update(basic_info)

                # add unique id
                twitter_location_unique_id = create_unique_id(data=twitter_location, schema="Location")
                twitter_location["nodeId"] = twitter_location_unique_id

                # remove possible None and empty values
                twitter_location = clean_dict(d=twitter_location)

                # check schema
                if check_schema(data=twitter_location, schema="Location"):
                    # add node to graph
                    nodes["Location"].append(twitter_location)

                    # add INCLUSION relationship
                    edges["INCLUSION"].append({"a": twitter_user_account_unique_id, "b": twitter_location_unique_id})

                    # add CO_OCCURRENCE relationship
                    if twitter_username_unique_id:
                        edges["CO_OCCURRENCE"].append(
                            {"a": twitter_username_unique_id, "b": twitter_location_unique_id}
                        )
            else:
                # reset
                twitter_location_unique_id = ""
        else:
            # reset
            twitter_location_unique_id = ""

        #######################################################################
        # Twitter person

        if x["twitter_profile"]["name"]:
            # information given in data
            twitter_person = extract_name(s=x["twitter_profile"]["name"])

            # add basic information
            twitter_person.update(basic_info)

            # add unique id
            twitter_person_unique_id = create_unique_id(data=twitter_person, schema="Person")
            twitter_person["nodeId"] = twitter_person_unique_id

            # remove possible None and empty values
            twitter_person = clean_dict(d=twitter_person)

            # check schema
            if check_schema(data=twitter_person, schema="Person"):
                # add node to graph
                nodes["Person"].append(twitter_person)

                # add INCLUSION relationship
                edges["INCLUSION"].append({"a": twitter_user_account_unique_id, "b": twitter_person_unique_id})

                # add CO_OCCURRENCE relationships
                if twitter_username_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": twitter_username_unique_id, "b": twitter_person_unique_id})
                if twitter_location_unique_id:
                    edges["CO_OCCURRENCE"].append({"a": twitter_location_unique_id, "b": twitter_person_unique_id})
        else:
            # reset
            twitter_person_unique_id = ""

        #######################################################################
        # Twitter domains

        if x["twitter_profile"]["url"]:
            # information given in data
            extracted_domains = extract_urls(s=x["twitter_profile"]["url"])

            if len(extracted_domains.items()) > 0:
                domains_unique_ids = []

                for d in extracted_domains.values():
                    twitter_domain = {"domain": d["domain"]}

                    # add basic information
                    twitter_domain.update(basic_info)

                    # add unique id
                    twitter_domain_unique_id = create_unique_id(data=twitter_domain, schema="Domain")
                    twitter_domain["nodeId"] = twitter_domain_unique_id

                    # remove possible None and empty values
                    twitter_domain = clean_dict(d=twitter_domain)

                    # check schema
                    if check_schema(data=twitter_domain, schema="Domain"):
                        # add node to graph
                        nodes["Domain"].append(twitter_domain)

                        # add INCLUSION relationship
                        edges["INCLUSION"].append({"a": twitter_user_account_unique_id, "b": twitter_domain_unique_id})

                        # add CO_OCCURRENCE relationships
                        if twitter_username_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": twitter_username_unique_id, "b": twitter_domain_unique_id}
                            )
                        if twitter_location_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": twitter_location_unique_id, "b": twitter_domain_unique_id}
                            )
                        if twitter_person_unique_id:
                            edges["CO_OCCURRENCE"].append(
                                {"a": twitter_person_unique_id, "b": twitter_domain_unique_id}
                            )
                        for i in domains_unique_ids:
                            edges["CO_OCCURRENCE"].append({"a": i, "b": twitter_domain_unique_id})

                        domains_unique_ids.append(twitter_domain_unique_id)
            else:
                # reset
                domains_unique_ids = []
        else:
            # reset
            domains_unique_ids = []

        # load data into database
        load_graph_into_db(nodes=nodes, edges=edges)


def evaluate_information_gain():
    """ Evaluate gain in information. """

    # Neo4j connection
    neo4j = neo4j_connect()

    # get data
    with neo4j.session() as session:

        # get usernames connecting accounts
        connecting_usernames = session.run(
            "MATCH (k:UserAccount)-[:INCLUSION]-(l:Username)-[:INCLUSION]-(m:UserAccount) WHERE k.platform='vk' AND m.platform='twitter' RETURN l.username as username"
        )
        connecting_usernames = [x["username"] for x in connecting_usernames.__iter__()]

    # save statistics
    connected_atoms_vk_total = {
        "Username": [],
        "Location": [],
        "Person": [],
        "Organization": [],
        "Phone": [],
        "Domain": [],
    }

    connected_atoms_twitter_total = {
        "Username": [],
        "Location": [],
        "Person": [],
        "Organization": [],
        "Phone": [],
        "Domain": [],
    }

    sigma = {
        "Username": [],
        "Location": [],
        "Person": [],
        "Organization": [],
        "Phone": [],
        "Domain": [],
        "total": [],
    }

    for u in tqdm(connecting_usernames, desc="usernames", total=len(connecting_usernames), unit="records"):
        # get vk data
        query = (
            "MATCH (k)-[:INCLUSION]-(l:UserAccount)-[:INCLUSION]-(m:Username) WHERE l.platform='vk' AND m.username='"
            + u
            + "' RETURN k.nodeId as nodeId, LABELS(k)[0] AS label"
        )
        connecting_atoms_vk = session.run(query)

        data_vk = {
            "Username": [],
            "Location": [],
            "Person": [],
            "Organization": [],
            "Phone": [],
            "Domain": [],
        }
        [data_vk[x["label"]].append(x["nodeId"]) for x in connecting_atoms_vk.__iter__()]

        # get twitter data
        query = (
            "MATCH (k)-[:INCLUSION]-(l:UserAccount)-[:INCLUSION]-(m:Username) WHERE l.platform='twitter' AND m.username='"
            + u
            + "' RETURN k.nodeId as nodeId, LABELS(k)[0] AS label"
        )
        connecting_atoms_twitter = session.run(query)

        data_twitter = {
            "Username": [],
            "Location": [],
            "Person": [],
            "Organization": [],
            "Phone": [],
            "Domain": [],
        }
        [data_twitter[x["label"]].append(x["nodeId"]) for x in connecting_atoms_twitter.__iter__()]

        # store statistics
        [connected_atoms_vk_total[k].append(len(v)) for k, v in data_vk.items()]
        [connected_atoms_twitter_total[k].append(len(v)) for k, v in data_twitter.items()]

        vk_atom_set_total = set()
        twitter_atom_set_total = set()

        for node_type in connected_atoms_vk_total.keys():
            # intersection/union of atom sets
            vk_set = set(data_vk[node_type])
            twitter_set = set(data_twitter[node_type])
            intersection = vk_set.intersection(twitter_set)
            union = vk_set.union(twitter_set)

            # store
            vk_atom_set_total = vk_atom_set_total.union(vk_set)
            twitter_atom_set_total = twitter_atom_set_total.union(twitter_set)

            # node type specific sigma
            if len(union) > 0:
                sigma[node_type].append(len(intersection) / len(union))

        intersection_total = vk_atom_set_total.intersection(twitter_atom_set_total)
        union_total = vk_atom_set_total.union(twitter_atom_set_total)
        sigma["total"].append(len(intersection_total) / len(union_total))

    # store results
    results = []

    for node_type in connected_atoms_vk_total.keys():
        vk_mean = np.mean(connected_atoms_vk_total[node_type]) if len(connected_atoms_vk_total[node_type]) > 0 else 0
        twitter_mean = (
            np.mean(connected_atoms_twitter_total[node_type])
            if len(connected_atoms_twitter_total[node_type]) > 0
            else 0
        )
        results.append(
            [
                node_type,
                np.round(vk_mean, 2),
                np.round(twitter_mean, 2),
                np.round(np.mean(sigma[node_type]), 2),
            ]
        )

    results.append(["sigma total", np.round(np.mean(sigma["total"]), 2), "", ""])

    table_plotter(
        data=results,
        filename="information_overlap_vk_twitter_user_accounts.png",
        title="Information overlap of VK and Twitter user accounts",
        param_plot={"figsize": (9, 12)},
        param_ax={
            "colLabels": ["", "$\\bf{VK}$", "$\\bf{Twitter}$", "$\sigma_e$"],
            "cellLoc": "left",
            "colLoc": "left",
            "loc": "upper center",
            "edges": "horizontal",
            "colWidths": [0.25, 0.25, 0.25, 0.25],
        },
    )


if __name__ == "__main__":
    # logging
    logging.basicConfig(
        filename=os.path.join(config("LOG_DIR"), "evaluation.log"),
        format=config("LOG_FORMAT"),
        level=config("LOG_LEVEL"),
        datefmt=config("LOG_DATEFMT"),
    )

    # execute requested procedure
    if sample:
        cross_network_user_sample()
    elif collect:
        collect_connected_twitter_accounts()
    elif evaluation:
        evaluate_information_gain()
    elif load:
        load_in_db()
    else:
        print("Please specify the evaluation procedure you want to execute.")
