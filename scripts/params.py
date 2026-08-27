from dataclasses import dataclass, field

from cimessages import MessageFormat
from purl import PurlRestrictedRl


@dataclass
class Params:  # pylint: disable=too-many-instance-attributes
    rl_portal_org: str
    rl_portal_group: str

    purl: PurlRestrictedRl
    message_reporter: MessageFormat
    timeout: int

    report_format: list[str]

    # Optional or with defaults
    rl_portal_host: str | None = None
    rl_portal_server: str | None = None

    replace: bool = False
    force: bool = False
    diff_with: str | None = None

    submit_only: bool = False
    report_path: str | None = None
    pack_safe: bool = False
    repro: bool = False  # will be extracted from the purl later

    # command rl-scan
    file_path: str | None = None
    filename: str | None = None

    # command rl-scan-url
    import_url: str | None = None

    auth_user: str | None = field(default=None, repr=False)
    auth_pass: str | None = field(default=None, repr=False)
    bearer_token: str | None = field(default=None, repr=False)

    debug: bool = False
