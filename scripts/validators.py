import os
from typing import List
from urllib.parse import (
    urlsplit,
    parse_qs,
)

from helpers import parse_report_formats

UPLOAD_FILE_SIZE_LIMIT = 10737418240  # 10GB


def validate_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise RuntimeError("File does not exist")

    if os.path.getsize(file_path) > UPLOAD_FILE_SIZE_LIMIT:
        raise RuntimeError("File size is larger than 10GB")


def validate_purl(purl: str) -> None:
    query = parse_qs(urlsplit(purl).query)
    if "build" in query and not ("version" in query["build"] or "repro" in query["build"]):
        raise RuntimeError("Wrong build type set, has to be either version or repro")


def validate_folder(report_path: str, report_format: str) -> None:
    if not report_path and not report_format:
        return

    if not report_path and report_format or report_path and not report_format:
        raise RuntimeError("Both report path and report format have to be provided for exporting")

    if (
        not os.path.exists(report_path)
        or os.path.exists(report_path)
        and not (os.path.isdir(report_path) and not os.listdir(report_path))
    ):
        raise RuntimeError("--report-path needs to point to an empty directory!")


def validate_report_formats(report_format: str) -> List[str]:
    if not report_format:
        return []

    return parse_report_formats(report_format)
