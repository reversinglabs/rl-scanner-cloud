import os
from typing import (
    List,
)

UPLOAD_FILE_SIZE_LIMIT = 50 * 1024 * 1024 * 1024  # 50GB

REPORT_FORMATS = {  # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    "cyclonedx": "report.cyclonedx.json",
    "sarif": "report.sarif.json",
    "spdx": "report.spdx.json",
    "rl-checks": "report.checks.json",
    "rl-cve": "report.cve.csv",
    "rl-json": "report.rl.json",
    "rl-summary-pdf": "report.summary.pdf",
    "rl-uri": "report.uri.csv",
}


_DEV = os.getenv("ENVIRONMENT", "") == "DEVELOPMENT"

SCANNER_COMMANDS: List[str] = [
    "rl-scan",
    "rl-scan-url",
    # "rl-scan-purl",
    # "rl-scan-docker",
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
