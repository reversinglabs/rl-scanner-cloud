from time import sleep
import requests
from cimessages import reporter
from helpers import (
    get_default_report_name,
    parse_report_formats,
)
from portal_api import PortalAPI

from constants import (
    _DEV,
    LOWER_ATTEMPT_TIMEOUT_MIN,
    UPPER_ATTEMPT_TIMEOUT_MIN,
    DEFAULT_ATTEMPT_TIMEOUT_MIN,
    ATTEMPT_TIMEOUT_SEC,
    DOWNLOAD_CHUNK_SIZE,
)


def get_scan_status(
    portal: PortalAPI,
    timeout: int,
    lower_attempt_timeout_min: int = LOWER_ATTEMPT_TIMEOUT_MIN,
    upper_attempt_timeout_min: int = UPPER_ATTEMPT_TIMEOUT_MIN,
    attempt_timeout_sec: int = ATTEMPT_TIMEOUT_SEC,
) -> str:
    if _DEV:
        lower_attempt_timeout_min = 1

    if timeout not in range(lower_attempt_timeout_min, upper_attempt_timeout_min):
        timeout = DEFAULT_ATTEMPT_TIMEOUT_MIN
        reporter.info(
            f"""
            Value of timeout parameter is out of bounds ({lower_attempt_timeout_min} - {upper_attempt_timeout_min}).
            Will set it to default {DEFAULT_ATTEMPT_TIMEOUT_MIN} minutes
        """
        )

    number_of_attempts = (timeout * 60) // attempt_timeout_sec

    while number_of_attempts > 0:
        reporter.info("Attempting to fetch analysis status")

        sleep(attempt_timeout_sec)
        response = portal.get_performed_checks()
        if response.status_code == 202:
            number_of_attempts -= 1
            continue

        return str(
            response.json()
            .get("analysis", {})
            .get("report", {})
            .get("info", {})
            .get("summary", {})
            .get("scan_status", "fail")
        )

    msg = "Preset timeout time expired"
    reporter.info(msg)
    raise RuntimeError(msg)


def get_analysis_url(
    request_invoker: PortalAPI,
) -> str:
    response = request_invoker.get_analysis_status()

    return str(
        response.json()
        .get(
            "analysis",
            {},
        )
        .get(
            "report",
            {},
        )
        .get(
            "info",
            {},
        )
        .get(
            "portal",
            {},
        )
        .get("reference"),
    )


def export_analysis_report(
    portal: PortalAPI,
    report_formats: str,
    report_path: str,
) -> None:
    for report_format in parse_report_formats(report_formats):
        reporter.info(f"Started {report_format} export")

        report_filename = get_default_report_name(report_format)
        response = portal.export_analysis_report(report_format)
        with open(f"{report_path}/{report_filename}", "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        reporter.info(f"Finished {report_format} export")


def export_pack_safe(
    portal: PortalAPI,
    report_path: str,
    chunk_size: int = DOWNLOAD_CHUNK_SIZE,
) -> None:
    response = portal.export_pack_safe()
    data = response.json()
    report_filename = data.get("file_name")
    download_url = data.get("download_link")

    reporter.info("Started rl-safe export")

    response = requests.get(download_url, stream=True)
    with open(f"{report_path}/{report_filename}", mode="wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            file.write(chunk)

    reporter.info("Finished rl-safe export")
