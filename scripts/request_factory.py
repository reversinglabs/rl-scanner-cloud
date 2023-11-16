import os

from cimessages import MessageFormat
from decorators import singleton

from requests import (
    request,
    Response,
)

from typing import (
    TypedDict,
    Optional,
    BinaryIO,
)


class Params(TypedDict):
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


@singleton
class RequestFactory:
    def __init__(self) -> None:
        self.api_token = os.environ.get("RLPORTAL_ACCESS_TOKEN")
        self.proxies = {}

        proxy_server = os.environ.get("RLSECURE_PROXY_SERVER", None)
        proxy_port = os.environ.get("RLSECURE_PROXY_PORT", None)
        proxy_user = os.environ.get("RLSECURE_PROXY_USER", None)
        proxy_password = os.environ.get("RLSECURE_PROXY_PASSWORD", None)

        if proxy_server is not None:
            self.proxies = {
                "http": f"http://{proxy_user}:{proxy_password}@{proxy_server}:{proxy_port}",
                "https": f"http://{proxy_user}:{proxy_password}@{proxy_server}:{proxy_port}",
            }

    def mk_url(self, params: Params, what: str) -> str:
        first = f"https://my.secure.software/{params.rl_portal_server}/api/public/v1/{what}/"

        second = f"{params.rl_portal_org}/{params.rl_portal_group}/{params.purl}"
        return first + second

    def post_scan_version_request(self, params: Params, file: BinaryIO) -> Response:
        # note https://peps.python.org/pep-0589/
        filename = params.filename if params.filename else os.path.basename(params.file_path)

        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/octet-stream",
        }

        query_params = {}
        for name in ["force", "replace", "diff_with"]:
            if name in params:
                query_params[name] = getattr(params, name)

        url = self.mk_url(params, "scan")

        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion
        return request(
            "POST",
            f"{url}",
            headers=headers,
            data=file,
            params=query_params,
            proxies=self.proxies,
        )

    def get_performed_checks_request(self, params: Params) -> Response:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        url = self.mk_url(params, "checks")

        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks
        return request(
            "GET",
            f"{url}",
            headers=headers,
            proxies=self.proxies,
        )