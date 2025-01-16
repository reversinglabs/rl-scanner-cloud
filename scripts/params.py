from dataclasses import dataclass
from typing import Optional

from cimessages import MessageFormat


@dataclass
class Params:  # pylint: disable=too-many-instance-attributes
    rl_portal_server: str
    rl_portal_org: str
    rl_portal_group: str
    purl: str
    file_path: str
    filename: str
    replace: Optional[bool]
    force: Optional[bool]
    diff_with: Optional[str]
    message_reporter: MessageFormat
    submit_only: Optional[bool]
    timeout: int
    report_path: Optional[str]
    report_format: Optional[str]
    pack_safe: bool = False
