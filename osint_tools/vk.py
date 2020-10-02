from decouple import config, Csv
from helpers.vk import get_vk_session


def get_vk_id(username: str) -> str:
    """ Returns vk.com ID of given username. """

    # get vk sessions
    vkapi = [get_vk_session(token=config("VK_TOKENS", cast=Csv())[i]) for i in range(6)][5]

    # getting ID
    try:
        username_id = vkapi.users.get(user_ids=[username], v=config("VK_API_VERSION"))[0]["id"]
        return str(username_id)
    except Exception as e:
        return None
