from typing import (
    List,
    Optional,
)

from constants import (
    REPORT_FORMATS,
    DEFAULT_DOMAIN,
)


def get_package_purl(
    purl: str,
) -> str:
    return purl.split("@")[0]


def get_version(
    purl: str,
) -> str:
    at_index = purl.find("@")
    build_index = purl.find("?")

    if build_index != -1:
        return purl[at_index + 1 : build_index]
    return purl[at_index + 1 :]


def has_repro(
    purl: str,
) -> bool:
    build_index = purl.find("?")

    if build_index == -1:
        return False
    return purl[build_index + 1 :] == "build=repro"


def _make_base_url(
    *,
    rl_portal_host: Optional[str] = None,
    rl_portal_server: Optional[str] = None,
    domain: str = DEFAULT_DOMAIN,
    proto: str = "https",
) -> str:
    # dont add the api tail, the report url is not part of the api
    if rl_portal_server in ["playground", "trial"]:  # special cases only on the default domain
        return f"{proto}://{rl_portal_server}.{domain}"

    if rl_portal_host:
        assert len(rl_portal_host) > 0

        if rl_portal_server:
            assert len(rl_portal_server) > 0
            return f"{proto}://{rl_portal_host}/{rl_portal_server}"  # both host and server(tenanat)

        return f"{proto}://{rl_portal_host}"  # only host, no server(tenant)

    assert rl_portal_server
    assert len(rl_portal_server) > 0

    return f"{proto}://my.{domain}/{rl_portal_server}"  # now we must have a server (tenant)


def get_portal_url(
    *,
    rl_portal_server: Optional[str] = None,
    rl_portal_host: Optional[str] = None,
    domain: str = DEFAULT_DOMAIN,
    proto: str = "https",
) -> str:
    return _make_base_url(
        rl_portal_server=rl_portal_server,
        rl_portal_host=rl_portal_host,
        domain=domain,
        proto=proto,
    )


def create_public_api_url(
    *,
    what: str,
    rl_portal_host: Optional[str] = None,
    rl_portal_server: Optional[str] = None,
    version: str = "v1",
) -> str:
    base_url = get_portal_url(
        rl_portal_host=rl_portal_host,
        rl_portal_server=rl_portal_server,
    )
    tail = f"api/public/{version}"

    return f"{base_url}/{tail}/{what}/"


def parse_report_formats(
    report_formats_csv: str,
) -> List[str]:
    parsed_report_formats = report_formats_csv.split(",")

    if "all" in parsed_report_formats:
        return list(REPORT_FORMATS.keys())

    # verify that the requested report is supported
    for maybe_report_format in parsed_report_formats:
        if maybe_report_format not in REPORT_FORMATS:
            msg = (
                "ERROR: Invalid report format provided: "
                + f"{maybe_report_format}, we currently suppport: {REPORT_FORMATS.keys()}."
            )
            raise RuntimeError(msg)

    return parsed_report_formats


def get_default_report_name(
    report_format: str,
) -> str:
    # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    if report_format in REPORT_FORMATS:
        return str(REPORT_FORMATS.get(report_format))

    assert False  # to get rid of mypy no return code
