GB = 1024 * 1024 * 1024
UPLOAD_FILE_SIZE_LIMIT = 50 * GB
REPORT_FILE_SIZE_LIMIT = 1 * GB

REPORT_FORMATS = {  # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    "cyclonedx": "report.cyclonedx.json",
    "rl-checks": "report.checks.json",
    "rl-cve": "report.cve.csv",
    # "rl-diff"
    "rl-json": "report.rl.json",
    "rl-summary-pdf": "report.summary.pdf",
    "rl-uri": "report.uri.csv",
    "sarif": "report.sarif.json",
    "spdx": "report.spdx.json",
}

SCANNER_COMMANDS: list[str] = [
    "rl-scan",
    "rl-scan-url",
]

EXIT_FATAL: int = 101

# IN MINUTES
LOWER_ATTEMPT_TIMEOUT_MIN = 10
UPPER_ATTEMPT_TIMEOUT_MIN = 1440  # 24h
DEFAULT_ATTEMPT_TIMEOUT_MIN = 20

# IN SECONDS
ATTEMPT_TIMEOUT_SEC: int = 30

CONNECT_TIMEOUT = 60
READ_TIMEOUT = 600  # 10 minutes
# REQUEST_TIMEOUT = 600  # 10 minutes
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

DOWNLOAD_CHUNK_SIZE: int = 16 * 1024  # 16k

DEFAULT_DOMAIN: str = "secure.software"

DESCRIPTION_TEXT = """
ReversingLabs: rl-scanner-cloud
Extended product documentation is available at: https://docs.secure.software
"""

EPILOG_TEXT = """
Environment variables:
  RLPORTAL_ACCESS_TOKEN    - Token used for access to the Portal
  RLSECURE_PROXY_SERVER    - Server (IP address or DNS name) for local proxy
  RLSECURE_PROXY_PORT      - Network port for local proxy
  RLSECURE_PROXY_USER      - User name for proxy authentication
  RLSECURE_PROXY_PASSWORD  - Password for proxy authentication
"""

EPILOG_TEXT_URL = f"""
{EPILOG_TEXT}
  RLPORTAL_AUTH_USER       - optional download user when not using token
  RLPORTAL_AUTH_PASS       - optional download password when not using token
  RLPORTAL_BEARER_TOKEN    - optional download bearer token
"""
