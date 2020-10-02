import instaloader


def get_instagram_id(username: str) -> str:
    """ Returns belonging Instagram ID given some username. """

    # instaloader instance
    L = instaloader.Instaloader()

    # get Instagram profile
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return str(profile.userid)
    except Exception as e:
        return None
