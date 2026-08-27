import argparse
import os
import re
import sys
import traceback
from collections.abc import Callable

from cimessages import MessageFormat, Messages
from constants import (
    DEFAULT_ATTEMPT_TIMEOUT_MIN,
    EXIT_FATAL,
    LOWER_ATTEMPT_TIMEOUT_MIN,
    REPORT_FORMATS,
    UPPER_ATTEMPT_TIMEOUT_MIN,
)
from params import Params
from purl import PurlRestrictedRl


def _purl_helper(arg: str) -> PurlRestrictedRl:
    try:
        return PurlRestrictedRl(arg)
    except Exception as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _csv_splitter(arg: str) -> list[str]:
    if not arg:
        return []

    supported_reports = list(REPORT_FORMATS.keys())
    supported_reports.append("all")

    rr: list[str] = []
    data = arg.split(",")
    if len(data) == 0:
        return []

    for item in data:
        if item:
            if item not in supported_reports:
                msg = f"Fatal: report format not supported: choose from: {supported_reports}"
                raise argparse.ArgumentTypeError(msg)
            rr.append(item)

    return sorted(rr)


def common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rl-portal-host",
        help="Portal Host that will do the scanning",
        required=False,
    )

    parser.add_argument(
        "--rl-portal-server",
        help="Portal tenant that will do the scanning",
        required=False,
    )

    parser.add_argument(
        "--rl-portal-org",
        required=True,
    )

    parser.add_argument(
        "--rl-portal-group",
        required=True,
    )

    parser.add_argument(
        "--purl",
        type=_purl_helper,
        required=True,
        help="Package URL used for the scan (format [pkg:namespace]/<project></package><@version>)",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the existing package version within the package, or reproducible build if build type is repro",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="If a package has the maximum number of versions, then the oldest version of the package will be "
        "deleted to make space for the version you're uploading",
    )

    parser.add_argument(
        "--repro",
        action="store_true",
        help="alternative way to specify a reproducible build like <purl>?build=repro",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="add additional verbosity during execution",
    )

    parser.add_argument(
        "--submit-only",
        action="store_true",
        help="Scan the file, and continue regardless of the scan outcome",
    )

    parser.add_argument(
        "--diff-with",
        help="Selected analyzed package version to compare against the uploaded version",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_ATTEMPT_TIMEOUT_MIN,
        help="Amount of time user is willing to wait for analysis before failing. Defaults to 20 minutes",
    )

    parser.add_argument(
        "--message-reporter",
        choices=list(MessageFormat),
        type=MessageFormat,
        default=MessageFormat.TEXT,
        help="Processing status message format",
    )

    supported_reports = ", ".join(list(REPORT_FORMATS.keys())) + ", all"
    parser.add_argument(
        "--report-format",
        type=_csv_splitter,
        help="A comma-separated list of report formats to generate. Supported values: "
        + f"{supported_reports}; needs --report-path to be specified",
        default=[],
    )

    parser.add_argument(
        "--report-path",
        help="Path to a directory where the selected reports will be saved",
    )

    parser.add_argument(
        "--pack-safe",
        action="store_true",
        help="Download a report.rl-safe archive into the report-path; needs --report-path to be specified",
    )


def validate_download_auth(params: Params) -> None:
    if params.auth_user and params.auth_pass:
        return
    if not params.auth_user and not params.auth_pass:
        return

    raise ValueError("Fatal: missing value when using '--auth-user' you must also use '--auth-pass' and vice versa")


def validate_tenant(t: str) -> None:
    # in the tenant we allow also underscore as it is not a dns name.
    word = r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?$"
    if t:
        if not re.match(word, t):
            raise ValueError("Fatal: portal_server (tenant) must be a valid word without '.'")


def validate_port(port: str) -> None:

    port_re = r"^\d{1,5}$"
    if not re.match(port_re, f"{port}"):
        raise ValueError("Fatal: port must be a a number")

    max_proxy_port = 65535
    valid: bool = 1 <= int(port) <= max_proxy_port
    if not valid:
        raise ValueError(f"Fatal: port must be in the range [1..{max_proxy_port}]")


def validate_portal_host(ph: str) -> None:
    part = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    h = rf"{part}(?:\.{part})*"
    host_re = rf"^{h}$"

    if ph:
        a = ph.split(":")
        if len(a) > 2:
            raise ValueError("Fatal: when specifying a 'host:port', only one ':' may be present in '--rl-portal-host'")

        host = a[0]
        if not re.match(host_re, host):
            raise ValueError(f"Fatal: portal_host must be a valid dns hostname: {ph}")

        if len(a) == 2:
            validate_port(a[1])


def validate_server_host(params: Params) -> None:
    if not params.rl_portal_server:  # actually the tenant used on the host
        params.rl_portal_server = None
    if params.rl_portal_server:
        validate_tenant(params.rl_portal_server)

    if not params.rl_portal_host:
        params.rl_portal_host = None
    if params.rl_portal_host:
        validate_portal_host(params.rl_portal_host)


def valid_timeout(reporter: Messages, timeout: int) -> int:
    change = False
    if timeout < LOWER_ATTEMPT_TIMEOUT_MIN:
        change = True
        timeout = LOWER_ATTEMPT_TIMEOUT_MIN

    if timeout > UPPER_ATTEMPT_TIMEOUT_MIN:
        change = True
        timeout = UPPER_ATTEMPT_TIMEOUT_MIN

    if change:
        ll = [
            f"Timeout parameter is out of bounds ({LOWER_ATTEMPT_TIMEOUT_MIN} - {UPPER_ATTEMPT_TIMEOUT_MIN}).",
            f"Has been set to: {timeout} minutes.",
        ]
        reporter.info("\n".join(ll))

    return timeout


def validate_report_folder(
    params: Params,
) -> None:
    report_format = params.report_format
    report_path = params.report_path
    pack_safe = params.pack_safe

    if report_format and not report_path:
        raise ValueError("Fatal: report-format needs a report-path to be specified")

    if pack_safe and not report_path:
        raise ValueError("Fatal: pack-safe needs a report-path to be specified")

    if report_path:
        does_not_exist = not os.path.exists(report_path)
        is_not_empty_dir = os.path.exists(report_path) and not (
            os.path.isdir(report_path) and not os.listdir(report_path)
        )
        if does_not_exist or is_not_empty_dir:
            raise ValueError("--report-path needs to point to an empty directory!")


def parse_report_formats(
    params: Params,
) -> list[str]:
    report_formats_in: list[str] = params.report_format

    if params.submit_only:
        return []

    if not report_formats_in:
        return []

    ll = sorted(REPORT_FORMATS.keys())
    if "all" in report_formats_in:
        return ll

    supported_reports = ", ".join(ll) + ", all"
    rr: list[str] = []
    for maybe_report_format in report_formats_in:
        z = maybe_report_format.strip()
        if z not in REPORT_FORMATS:
            msg = (
                "Fatal: Invalid report format provided: "
                + f"{maybe_report_format}, we currently support: {supported_reports}."
            )
            raise ValueError(msg)
        else:
            if z not in rr:
                rr.append(z)

    if len(rr):
        return sorted(rr)

    raise ValueError("Fatal: no report formats specified")


def runner(xmain: Callable[[], int]) -> None:
    prog = os.path.basename(sys.argv[0])

    try:
        rr: int = xmain()
        sys.exit(rr)
    except Exception as e:
        print(f"Error: {prog}: {str(e)}", file=sys.stderr)
        if "--debug" in sys.argv:  # params may not exist yet
            traceback.print_exc()
        sys.exit(EXIT_FATAL)
