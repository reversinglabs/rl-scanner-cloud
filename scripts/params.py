from dataclasses import dataclass
from typing import Optional

from cimessages import MessageFormat


@dataclass
class Params:  # pylint: disable=too-many-instance-attributes
    rl_portal_org: str
    rl_portal_group: str
    purl: str
    file_path: str
    filename: str
    message_reporter: MessageFormat
    timeout: int
    pack_safe: bool = False

    rl_portal_host: Optional[str] = None
    rl_portal_server: Optional[str] = None

    replace: Optional[bool] = None
    force: Optional[bool] = None

    diff_with: Optional[str] = None

    submit_only: Optional[bool] = None
    report_path: Optional[str] = None
    report_format: Optional[str] = None

    debug: Optional[bool] = None
