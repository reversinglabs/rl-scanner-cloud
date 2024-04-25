import os
import sys
from typing import BinaryIO

import requests
from requests import Response
from requests.exceptions import HTTPError, JSONDecodeError

from cimessages import reporter
from helpers import create_public_api_url, has_repro, get_version, get_package_purl
from params import Params

REQUEST_TIMEOUT = 600  # 10 minutes


def _transform_purl(purl: str) -> str:
    if not purl.startswith("pkg:rl/"):
        return f"pkg:rl/{purl}"

    return purl


class PortalAPI:
    def __init__(self, params: Params) -> None:
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

        self.params = params
        # update params.purl, params.force and params.replace if necessary
        self._transform_params()

    def scan_version(self, file: BinaryIO) -> Response:
        params = self.params
        filename = params.filename if params.filename else os.path.basename(params.file_path)

        headers = self._auth_header() | {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/octet-stream",
        }

        query_params = {}
        for name in ["force", "replace", "diff_with"]:
            if getattr(params, name, False):
                query_params[name] = getattr(params, name)

        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion
        response = requests.post(
            self._public_api_url_to("scan", params.purl),
            headers=headers,
            proxies=self.proxies,
            data=file,
            params=query_params,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(response)
        return response

    def get_performed_checks(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks
        response = requests.get(
            self._public_api_url_to("checks", self.params.purl),
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(response)
        return response

    def export_analysis_report(self, report_format: str) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        response = requests.get(
            self._public_api_url_to("report", f"{report_format}/{self.params.purl}"),
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(response, should_exit=False)
        return response

    def get_analysis_status(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionStatus
        response = requests.get(
            self._public_api_url_to("status", self.params.purl),
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(response, should_exit=False)
        return response

    def get_package_versions(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Package/operation/listVersions
        response = requests.get(
            self._public_api_url_to("list", get_package_purl(self.params.purl)),
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
        )

        return response

    def _public_api_url_to(self, what: str, path: str) -> str:
        params = self.params
        public_api_url = create_public_api_url(params.rl_portal_server, what)
        return f"{public_api_url}{params.rl_portal_org}/{params.rl_portal_group}/{path}"

    def _check_and_handle_http_error(self, response: Response, should_exit: bool = True) -> None:
        try:
            response.raise_for_status()
        except HTTPError as http_error:
            try:
                default_err_msg = f"Something went wrong with analysis report export {http_error}"
                error_message = http_error.response.json()
                reporter.info(error_message.get("error", default_err_msg))
            except JSONDecodeError as json_decode_error:
                reporter.info(f"Something went wrong with your request {json_decode_error}")

            if should_exit:
                sys.exit(101)

    def _auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
        }

    def _transform_params(self) -> None:
        self.params.purl = _transform_purl(self.params.purl)
        self._transform_force_and_replace_params()

    def _transform_force_and_replace_params(self) -> None:
        if not (self.params.force and self.params.replace):
            return

        # both are true
        if has_repro(self.params.purl):
            # force is a illegal option on repro
            self.params.force = False
            return

        response = self.get_package_versions()
        if response.status_code not in [200, 404]:
            msg = (
                f"Error: while validating force and replace parameters: get_package_versions(): {response.status_code}"
            )
            raise RuntimeError(msg)

        if response.status_code == 404:
            # if we have no versions at all we dont need replace or force
            self.params.replace = False
            self.params.force = False
            return

        if response.status_code == 200:
            data = response.json()
            purl_version = get_version(self.params.purl)
            version_exists = [version for version in data.get("versions") if version.get("version") == purl_version]
            if version_exists:
                # when we have replace:True, we dont need force:True at all
                self.params.force = False
            else:
                # this version does not exist so we dont need replace, but we may need force
                self.params.replace = False

        return
