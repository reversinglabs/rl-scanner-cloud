import os
from typing import (
    List,
)

UPLOAD_FILE_SIZE_LIMIT = 10 * 1024 * 1024 * 1024  # 10GB

REPORT_FORMATS = {  # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    "sarif": "report.sarif.json",
    "cyclonedx": "report.cyclonedx.json",
    "spdx": "report.spdx.json",
    "rl-json": "report.rl.json",
    "rl-checks": "report.checks.json",
    "rl-cve": "report.cve.csv",
    "rl-uri": "report.uri.csv",
    "rl-summary-pdf": "report.summary.pdf",
}

_DEV = os.getenv("ENVIRONMENT", "") == "DEVELOPMENT"

SCANNER_COMMANDS: List[str] = [
    "rl-scan",
]

EXIT_FATAL: int = 101

# IN MINUTES
LOWER_ATTEMPT_TIMEOUT_MIN = 10
UPPER_ATTEMPT_TIMEOUT_MIN = 1440  # 24h
DEFAULT_ATTEMPT_TIMEOUT_MIN = 20

# IN SECONDS
ATTEMPT_TIMEOUT_SEC: int = 30
REQUEST_TIMEOUT = 600  # 10 minutes

DOWNLOAD_CHUNK_SIZE: int = 16 * 1024  # 16k

DEFAULT_DOMAIN: str = "secure.software"
