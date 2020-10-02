from pymongo import MongoClient
from decouple import config


def mongodb_connect() -> "pymongo.mongo_client.MongoClient, pymongo.database.Database":
    """ Connection to MongoDB """

    client = MongoClient(
        "mongodb://%s:%s@%s:%s/%s"
        % (config("DB_USER"), config("DB_PW"), config("DB_HOST"), config("DB_PORT"), config("DB_NAME"))
    )

    db = client[config("DB_NAME")]

    return client, db
