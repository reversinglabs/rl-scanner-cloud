from time import sleep

from cimessages import reporter
from helpers import get_default_report_name, parse_report_formats
from portal_api import PortalAPI

DEFAULT_ATTEMPT_TIMEOUT_MIN = 20


def get_scan_status(portal: PortalAPI, timeout: int) -> str:
    attempt_timeout_sec = 30
    lower_attempt_timeout_min = 10
    upper_attempt_timeout_min = 1440  # 24h

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

    reporter.info("Preset timeout time expired")
    return "fail"


def get_analysis_url(request_invoker: PortalAPI) -> str:
    response = request_invoker.get_analysis_status()

    return str(response.json().get("analysis", {}).get("report", {}).get("info", {}).get("portal", {}).get("reference"))


def export_analysis_report(portal: PortalAPI, report_formats: str, report_path: str) -> None:
    for report_format in parse_report_formats(report_formats):
        response = portal.export_analysis_report(report_format)
        reporter.info(f"Started {report_format} export")

        report_filename = get_default_report_name(report_format)

        with open(f"{report_path}/{report_filename}", "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
            reporter.info(f"Finished {report_format} export")
