from typing import (
    TypedDict,
    Optional,
)

from cimessages import MessageFormat


class Params(TypedDict):
    rl_portal_server: str
    rl_portal_org: str
    rl_portal_group: str
    purl: str
    file_path: str
    report_path: str
    filename: str
    replace: Optional[bool]
    force: Optional[bool]
    diff_with: Optional[str]
    message_reporter: MessageFormat
    submit_only: Optional[bool]
    timeout: int
