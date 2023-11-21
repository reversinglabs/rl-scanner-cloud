def get_package_purl(purl: str) -> str:
    return purl.split("@")[0]


def get_version(purl: str):
    at_index = purl.find("@")
    build_index = purl.find("?")

    if build_index != -1:
        return purl[at_index + 1 : build_index]
    else:
        return purl[at_index + 1 :]


def has_repro(purl: str):
    build_index = purl.find("?")

    if build_index == -1:
        return False

    else:
        return purl[build_index + 1 :] == "build=repro"
