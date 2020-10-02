import os

import pandas as pd
from decouple import config

# Alexa 1 Mio
ALEXA1M = pd.read_csv(os.path.join(config("DATA_DIR"), "./top-1m-alexa.csv"), sep=",", header=None, skiprows=1)[
    1
].to_list()

# Social Media Platforms
SOCIAL_MEDIA_PLATFORMS = ["youtube", "facebook", "reddit", "vk", "instagram", "twitter"]