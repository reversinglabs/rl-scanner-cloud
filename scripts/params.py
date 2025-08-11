from dataclasses import dataclass
from typing import Optional

from cimessages import MessageFormat


@dataclass
class Params:  # pylint: disable=too-many-instance-attributes
    rl_portal_org: str
    rl_portal_group: str

    purl: str
    message_reporter: MessageFormat
    timeout: int

    # Optional or with defaults
    rl_portal_host: Optional[str] = None
    rl_portal_server: Optional[str] = None

    replace: Optional[bool] = None
    force: Optional[bool] = None
    diff_with: Optional[str] = None

    submit_only: Optional[bool] = None
    report_path: Optional[str] = None
    report_format: Optional[str] = None
    pack_safe: bool = False

    # command rl-scan
    file_path: Optional[str] = None
    filename: Optional[str] = None

    # command rl-scan-url
    import_url: Optional[str] = None
    # import_docker: Optional[str] = None

    auth_user: Optional[str] = None
    auth_pass: Optional[str] = None
    bearer_token: Optional[str] = None

    debug: Optional[bool] = None
