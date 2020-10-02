import tweepy

from decouple import config


def get_twitter_user(username: str) -> "tweepy.models.User":
    """ Returns Twitter user profile given the username. """

    # Twitter API credentials
    consumer_key = config("TWITTER_CONSUMER_KEY")
    consumer_secret = config("TWITTER_CONSUMER_SECRET")
    access_token = config("TWITTER_ACCESS_TOKEN")
    access_token_secret = config("TWITTER_ACCESS_TOKEN_SECRET")

    # authorization of consumer key and consumer secret
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

    # set access to user's access key and access secret
    auth.set_access_token(access_token, access_token_secret)

    # calling the api
    api = tweepy.API(auth)

    # get user profile
    try:
        user = api.get_user(username)
        return user
    except tweepy.error.TweepError:
        return None
