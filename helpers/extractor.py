import re
from typing import Dict

import tldextract

from helpers.data_static import SOCIAL_MEDIA_PLATFORMS
from helpers.misc import remove_emojis


def extract_name(s: str) -> dict:
    """ Extract name properties from string. """

    # remove Emojis and leading/ending spaces
    s_cleaned = remove_emojis(s)

    # case 'Doe, Joe'
    comma_split = s_cleaned.split(",")
    if len(comma_split) == 2:
        return {"familyName": comma_split[0].strip(), "givenName": comma_split[1].strip(), "rawData": s}

    # case 'Joe Doe' or 'Joe Dean Doe'
    white_space_split = s_cleaned.split(" ")
    if len(white_space_split) > 1:
        return {"familyName": white_space_split[-1].strip(), "givenName": white_space_split[0].strip(), "rawData": s}

    return {"rawData": s}


def extract_media_info(s: str) -> dict:
    """ Extract media properties from string. """

    result = {}

    ###############################################################################################
    # format

    extensions = (
        "odt",
        "sh",
        "tif",
        "swift",
        "csv",
        "part",
        "avi",
        "ico",
        "mpeg",
        "docx",
        "odp",
        "emlx",
        "rss",
        "m4v",
        "mp4",
        "js",
        "fnt",
        "mp3",
        "class",
        "doc",
        "ogg",
        "msg",
        "cs",
        "arj",
        "cgi",
        "7z",
        "ttf",
        "oft",
        "jsp",
        "3gp",
        "pl",
        "html",
        "cpp",
        "h",
        "midi",
        "dmg",
        "fon",
        "asp",
        "cda",
        "bin",
        "cab",
        "flv",
        "ai",
        "pst",
        "c",
        "ini",
        "tar",
        "sql",
        "mpg",
        "cfg",
        "htm",
        "xls",
        "vcf",
        "dat",
        "exe",
        "sys",
        "com",
        "pptx",
        "ppt",
        "apk",
        "icns",
        "otf",
        "pdf",
        "ps",
        "gadget",
        "vob",
        "tiff",
        "mov",
        "tar.gz",
        "php",
        "jpeg",
        "aif",
        "java",
        "swf",
        "3g2",
        "wmv",
        "mpa",
        "lnk",
        "aspx",
        "dbf",
        "ost",
        "mid",
        "jar",
        "wav",
        "png",
        "xlsm",
        "cfm",
        "deb",
        "drv",
        "tmp",
        "cur",
        "sav",
        "z",
        "h264",
        "rar",
        "eml",
        "wma",
        "msi",
        "rtf",
        "wsf",
        "bmp",
        "vcd",
        "gif",
        "xml",
        "dll",
        "jpg",
        "pkg",
        "css",
        "psd",
        "txt",
        "mdb",
        "vb",
        "bat",
        "pps",
        "wpd",
        "cpl",
        "email",
        "xlsx",
        "zip",
        "bak",
        "cer",
        "svg",
        "db",
        "rm",
        "wpl",
        "py",
        "rpm",
        "ods",
        "iso",
        "xhtml",
        "tex",
        "toast",
        "log",
        "mkv",
        "dmp",
        "key",
    )

    # handle url case
    url_split = s.split("/")
    if len(url_split) > 1:
        s = url_split[-1]

    # handle 'file.doc?foo'
    s = s.split("?")[0]

    # extract format
    if s.endswith(extensions):
        extensions_split = s.split(".")
        # handle case 'www.test.com'; com is also extension
        if len(extensions_split) == 2:
            result["format"] = s.split(".")[1]

    ###############################################################################################
    # dimensions

    dimensions = re.findall(r"[1-9]\d{1,4}x[1-9]\d+", s)
    if len(dimensions) > 0:
        dimensions = dimensions[0].split("x")
        result["width"] = int(dimensions[0])
        result["height"] = int(dimensions[-1])

    return result


def extract_urls(s: str) -> Dict[str, Dict[str, str]]:
    """ Extracting URLs and its components. """

    # extract URLs
    url_pattern = re.compile(
        r"\b((?:https?://)?(?:(?:www\.)?(?:[\da-z\.-]+)\.(?:[a-z]{2,6})|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])))(?::[0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])?(?:/[\w\.-]*)*/?)\b"
    )
    urls_in_string = url_pattern.findall(s)

    result = dict()

    # split URL in components
    for u in urls_in_string:
        # extract
        ext = tldextract.extract(u)
        domain = ext.registered_domain
        if domain == "":
            continue
        elif ext.subdomain:
            subdomain = ext.subdomain + "." + ext.registered_domain
        else:
            subdomain = ""

        # extract username from URL, e.g., vk.com/john_doe
        username = ""
        platform = ext.domain
        if platform in SOCIAL_MEDIA_PLATFORMS:
            url = u
            if platform == "youtube" and url.split("/")[-1] == "featured":
                url = "/".join(url.split("/")[:-1])
            if url[-1] == "/":
                url = url[:-1]

            username = url.split("/")[-1]

        # extract path from url
        path = u.split(domain)[-1]

        # store
        result[u] = {
            "domain": ext.registered_domain,
            "subdomain": subdomain,
            "username": username,
            "platform": platform if username else "",
            "path": path,
        }

    return result


def extract_facebook_id(s: str) -> str:
    """ Extracts Facebook ID from given string. """

    # check if + is at beginning
    if s[0] == "+":
        s = s[1:]

    # check if string can be coverted to number
    try:
        int(s)
    except ValueError:
        return None

    return s
