import os

from decorators import singleton
from requests import request, Response
from params import Params
from helpers import get_package_purl
from typing import BinaryIO


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

    def create_url(self, params: Params, what: str) -> str:
        if params.rl_portal_server == "trial":
            return f"https://trial.secure.software/api/public/v1/{what}/"

        if params.rl_portal_server == "playground":
            return f"https://playground.secure.software/api/public/v1/{what}/"

        return f"https://my.secure.software/{params.rl_portal_server}/api/public/v1/{what}/"

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

        url = self.create_url(params, "scan")
        url = f"{url}{params.rl_portal_org}/{params.rl_portal_group}/{params.purl}"

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

        url = self.create_url(params, "checks")
        url = f"{url}{params.rl_portal_org}/{params.rl_portal_group}/{params.purl}"

        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks
        return request(
            "GET",
            f"{url}",
            headers=headers,
            proxies=self.proxies,
        )

    def get_export_analysis_report_request(self, params: Params, report_format: str) -> Response:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        url = self.create_url(params, "report")
        url = f"{url}{params.rl_portal_org}/{params.rl_portal_group}/{report_format}/{params.purl}"

        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        return request(
            "GET",
            f"{url}",
            headers=headers,
            proxies=self.proxies,
        )

    def get_package_versions(self, params: Params) -> Response:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        url = self.create_url(params, "list")

        package_purl = get_package_purl(params.purl)
        url = f"{url}{params.rl_portal_org}/{params.rl_portal_group}/{package_purl}"

        # https://docs.secure.software/api-reference/#tag/Package/operation/listVersions
        return request(
            "GET",
            f"{url}",
            headers=headers,
            proxies=self.proxies,
        )
