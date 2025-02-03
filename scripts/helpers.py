from typing import List

RF = {  # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    "sarif": "report.sarif.json",
    "cyclonedx": "report.cyclonedx.json",
    "spdx": "report.spdx.json",
    "rl-json": "report.rl.json",
    "rl-checks": "report.checks.json",
    "rl-cve": "report.cve.csv",
    "rl-uri": "report.uri.csv",
    "rl-summary-pdf": "report.summary.pdf",
}


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


def get_portal_url(
    rl_portal_server: str,
) -> str:
    if rl_portal_server == "trial":
        return "https://trial.secure.software"

    if rl_portal_server == "playground":
        return "https://playground.secure.software"

    return f"https://my.secure.software/{rl_portal_server}"


def create_public_api_url(
    rl_portal_server: str,
    what: str,
) -> str:
    url = get_portal_url(rl_portal_server)
    return f"{url}/api/public/v1/{what}/"


def parse_report_formats(
    report_formats_csv: str,
) -> List[str]:
    parsed_report_formats = report_formats_csv.split(",")

    if "all" in parsed_report_formats:
        return list(RF.keys())

    # verify that the requested report is supported
    for maybe_report_format in parsed_report_formats:
        if maybe_report_format not in RF:
            raise RuntimeError(
                f"ERROR: Invalid report format provided: {maybe_report_format}, we currently suppport: {RF.keys()}."
            )

    return parsed_report_formats


def get_default_report_name(
    report_format: str,
) -> str:
    # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    if report_format in RF:
        return str(RF.get(report_format))

    assert False  # to get rid of mypy no return code
