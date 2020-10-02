import re
from typing import Dict, List

import spacy

from helpers.date_time import get_standardized_now
from helpers.extractor import extract_urls
from helpers.misc import clean_dict, remove_emojis
from helpers.schema import check_schema, create_unique_id


def ner(s: str) -> Dict[str, List[str]]:
    """ Named entity recognition. """

    # load model
    nlp = spacy.load("de_core_news_sm")

    # cleaning text
    # remove Emojis and leading/ending spaces
    s = remove_emojis(s)

    # remove whitespaces, tabs and line breaks
    s = re.sub("[\s]{2,}", " ", s)

    # urls
    urls = list(extract_urls(s).keys())
    for u in urls:
        s = s.replace(u, " ")

    # processing
    doc = nlp(s)
    # store extracted entities
    extracted_entities = {"Organization": []}

    for ent in doc.ents:
        if ent.label_ == "ORG" and "!" not in ent.text:
            organization = {
                "name": ent.text,
                "timestamp": get_standardized_now(),
                "schemaVersion": 0.1,
                "rawData": ent.text,
            }
            # add node ID
            organization_unique_id = create_unique_id(data=organization, schema="Organization")
            organization["nodeId"] = organization_unique_id

            # check schema
            if check_schema(data=organization, schema="Organization"):
                extracted_entities["Organization"].append(organization)

    return clean_dict(extracted_entities)
