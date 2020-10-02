import vk


def get_vk_session(token):
    """
    :param token: token for vk.com API; str
    :return: session; obj
    """
    # VK session
    session = vk.Session(access_token=token)
    vkapi = vk.API(session)

    return vkapi
