import hashlib


def create_hash(s: str) -> str:
    """ Create SHA 256 hash value from string (defined in FIPS 180-2) """

    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def get_checksum(file: str) -> str:
    """ SHA256 checksum/hash value of file (defined in FIPS 180-2) """

    return hashlib.sha256(open(file, "rb").read()).hexdigest()
