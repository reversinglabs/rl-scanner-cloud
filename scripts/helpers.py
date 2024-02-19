from typing import List


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


def get_portal_url(rl_portal_server: str) -> str:
    if rl_portal_server == "trial":
        return "https://trial.secure.software"

    if rl_portal_server == "playground":
        return "https://playground.secure.software"

    return f"https://my.secure.software/{rl_portal_server}"


def create_public_api_url(rl_portal_server: str, what: str) -> str:
    url = get_portal_url(rl_portal_server)
    return f"{url}/api/public/v1/{what}/"


def parse_report_formats(report_formats_csv: str) -> List[str]:
    valid_report_formats = ["sarif", "cyclonedx", "spdx", "rl-json", "rl-checks"]
    parsed_report_formats = report_formats_csv.split(",")

    for maybe_report_format in parsed_report_formats:
        if maybe_report_format == "all":
            return valid_report_formats

        if maybe_report_format not in valid_report_formats:
            raise RuntimeError(f"Invalid report format provided: {maybe_report_format}")

    return parsed_report_formats


def get_default_report_name(report_format: str):
    # https://docs.secure.software/cli/commands/report?_highlight=report&_highlight=format#usage
    if report_format == "sarif":
        return "report.sarif.json"
    if report_format == "cyclonedx":
        return "report.cyclonedx.json"
    if report_format == "spdx":
        return "report.spdx.json"
    if report_format == "rl-json":
        return "report.rl.json"
    if report_format == "rl-checks":
        return "report.checks.json"
