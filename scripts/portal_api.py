import os
import sys
from typing import BinaryIO

import requests
from requests import Response
from requests.exceptions import HTTPError, JSONDecodeError

from cimessages import reporter
from helpers import create_public_api_url, has_repro, get_version, get_package_purl
from params import Params


def _transform_purl(purl) -> str:
    if not purl.startswith("pkg:rl/"):
        return f"pkg:rl/{purl}"

    return purl


class PortalAPI:
    def __init__(self, params: Params):
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
        )

        self._check_and_handle_http_error(response)
        return response

    def get_performed_checks(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks
        response = requests.get(
            self._public_api_url_to("checks", self.params.purl), headers=self._auth_header(), proxies=self.proxies
        )

        self._check_and_handle_http_error(response)
        return response

    def export_analysis_report(self, report_format: str) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        response = requests.get(
            self._public_api_url_to("report", f"{report_format}/{self.params.purl}"),
            headers=self._auth_header(),
            proxies=self.proxies,
        )

        self._check_and_handle_http_error(response, should_exit=False)
        return response

    def get_analysis_status(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionStatus
        response = requests.get(
            self._public_api_url_to("status", self.params.purl), headers=self._auth_header(), proxies=self.proxies
        )

        self._check_and_handle_http_error(response, should_exit=False)
        return response

    def get_package_versions(self) -> Response:
        # https://docs.secure.software/api-reference/#tag/Package/operation/listVersions
        response = requests.get(
            self._public_api_url_to("list", get_package_purl(self.params.purl)),
            headers=self._auth_header(),
            proxies=self.proxies,
        )

        return response

    def _public_api_url_to(self, what: str, path: str):
        params = self.params
        public_api_url = create_public_api_url(params.rl_portal_server, what)
        return f"{public_api_url}{params.rl_portal_org}/{params.rl_portal_group}/{path}"

    def _check_and_handle_http_error(self, response: Response, should_exit: bool = True):
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

    def _auth_header(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
        }

    def _transform_params(self):
        self.params.purl = _transform_purl(self.params.purl)
        params = self._transform_force_and_replace_params()
        return params

    def _transform_force_and_replace_params(self):
        params = self.params
        if params.force and params.replace:
            if has_repro(params.purl):
                params.force = False
                return params

            response = self.get_package_versions()
            if response.status_code == 404:
                params.replace = False
                params.force = False

            elif response.status_code == 200:
                data = response.json()
                purl_version = get_version(params.purl)
                version_exists = [version for version in data.get("versions") if version.get("version") == purl_version]
                if version_exists:
                    params.force = False
                else:
                    params.replace = False

            else:
                raise RuntimeError("Something went wrong while validating force and replace parameters")
