import os
import sys
from typing import (
    BinaryIO,
    Dict,
    Any,
)

import requests
from requests import Response
from requests.exceptions import (
    HTTPError,
    JSONDecodeError,
)

from cimessages import reporter
from helpers import (
    create_public_api_url,
    has_repro,
    get_version,
    get_package_purl,
)
from params import Params

from constants import (
    REQUEST_TIMEOUT,
    EXIT_FATAL,
)


def _transform_purl(
    purl: str,
) -> str:
    k = "pkg:rl"
    if not purl.startswith(k):
        return f"{k}/{purl}"

    return purl


class PortalAPI:
    def __init__(
        self,
        params: Params,
    ) -> None:
        self.params: Params = params
        self.api_token: str = str(os.environ.get("RLPORTAL_ACCESS_TOKEN"))
        self.proxies: Dict[str, str] = {}

        proxy_server = os.environ.get("RLSECURE_PROXY_SERVER", None)
        if proxy_server and len(proxy_server) == 0:
            proxy_server = None
        proxy_port = os.environ.get("RLSECURE_PROXY_PORT", None)
        if proxy_port and len(proxy_port) == 0:
            proxy_port = None
        proxy_user = os.environ.get("RLSECURE_PROXY_USER", None)
        if proxy_user and len(proxy_user) == 0:
            proxy_user = None
        proxy_password = os.environ.get("RLSECURE_PROXY_PASSWORD", None)
        if proxy_password and len(proxy_password) == 0:
            proxy_password = None

        if proxy_server is not None:
            self.proxies = {
                "http": f"http://{proxy_user}:{proxy_password}@{proxy_server}:{proxy_port}",
                "https": f"http://{proxy_user}:{proxy_password}@{proxy_server}:{proxy_port}",
            }

        # update params.purl, params.force and params.replace if necessary
        self.params.purl = _transform_purl(self.params.purl)
        self._transform_force_and_replace_params()

    def _transform_force_and_replace_params(
        self,
    ) -> None:
        if not (self.params.force and self.params.replace):
            return

        # both are true
        if has_repro(self.params.purl):
            # force is a illegal option on repro
            self.params.force = False
            return

        response = self.get_package_versions()
        if response.status_code not in [200, 404, 401]:
            msg = (
                f"Error: while validating force and replace parameters: get_package_versions(): {response.status_code}"
            )
            raise RuntimeError(msg)

        if response.status_code in [404, 401]:
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

    def _public_api_url_to(
        self,
        *,
        what: str,
        path: str,
    ) -> str:
        params = self.params

        if not params.rl_portal_host:
            params.rl_portal_host = None

        if not params.rl_portal_server:
            params.rl_portal_server = None

        public_api_url = create_public_api_url(
            rl_portal_host=params.rl_portal_host,
            rl_portal_server=params.rl_portal_server,
            what=what,
        )

        return f"{public_api_url}{params.rl_portal_org}/{params.rl_portal_group}/{path}"

    def _check_and_handle_http_error(
        self,
        url: str,
        response: Response,
        should_exit: bool = True,
    ) -> None:
        try:
            if self.params.debug:
                print(url, response.status_code, file=sys.stderr)
            response.raise_for_status()
        except HTTPError as http_error:
            if self.params.debug:
                print(http_error, file=sys.stderr)

            try:

                default_err_msg = f"Something went wrong with analysis report export {http_error}"
                error_message = http_error.response.json()
                reporter.error(error_message.get("error", default_err_msg))
            except JSONDecodeError as json_decode_error:
                reporter.error(f"Something went wrong with your request {json_decode_error}")

            if should_exit:
                sys.exit(EXIT_FATAL)

    def _auth_header(
        self,
    ) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "rl-scanner-cloud",
        }

    def _do_get(self, url: str) -> Response:
        return requests.get(
            url,
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
        )

    # Public
    # todo: scan_version_url
    # todo: scan_version_docker
    def scan_file_version(
        self,
        *,
        file_stream: BinaryIO,
        file_name: str,
    ) -> Response:
        params = self.params

        headers = self._auth_header() | {
            "Content-Disposition": f"attachment; filename={file_name}",
            "Content-Type": "application/octet-stream",
        }

        query_params = {}
        for name in [
            "force",
            "replace",
            "diff_with",
        ]:
            if getattr(params, name, False):
                query_params[name] = getattr(params, name)

        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion
        url = self._public_api_url_to(
            what="scan",
            path=params.purl,
        )
        response = requests.post(
            url,
            headers=headers,
            proxies=self.proxies,
            data=file_stream,
            params=query_params,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(
            url,
            response,
        )
        return response

    def scan_import_url_version(
        self,
        *,
        import_url: str,
    ) -> Response:
        headers: Dict[str, str] = self._auth_header() | {
            "Content-Type": "application/json",
        }
        qp_names = [
            "force",
            "replace",
            "diff_with",
        ]
        query_params: Dict[str, Any] = {}
        for name in qp_names:
            if getattr(self.params, name, False):
                query_params[name] = getattr(self.params, name)

        data: Dict[str, Any] = {
            "url": import_url,
        }

        if self.params.bearer_token:
            data["bearer-token"] = self.params.bearer_token
        else:
            if self.params.auth_user:
                data["auto-user"] = self.params.auth_user
            if self.params.auth_pass:
                data["auto-pass"] = self.params.auth_pass

        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion
        url = self._public_api_url_to(
            what="url-import",
            path=self.params.purl,
        )

        response = requests.post(
            url,
            headers=headers,
            proxies=self.proxies,
            json=data,
            params=query_params,
            timeout=REQUEST_TIMEOUT,
        )

        self._check_and_handle_http_error(
            url,
            response,
        )
        return response

    def get_performed_checks(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks
        url = self._public_api_url_to(
            what="checks",
            path=self.params.purl,
        )
        response = self._do_get(url)
        self._check_and_handle_http_error(
            url,
            response,
        )
        return response

    def export_analysis_report(
        self,
        report_format: str,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        url = self._public_api_url_to(
            what="report",
            path=f"{report_format}/{self.params.purl}",
        )
        response = self._do_get(url)
        self._check_and_handle_http_error(
            url,
            response,
            should_exit=False,
        )
        return response

    def export_pack_safe(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        url = self._public_api_url_to(
            what="pack/safe",
            path=f"{self.params.purl}",
        )
        response = self._do_get(url)
        self._check_and_handle_http_error(
            url,
            response,
            should_exit=False,
        )
        return response

    def get_analysis_status(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionStatus
        url = self._public_api_url_to(
            what="status",
            path=self.params.purl,
        )
        response = self._do_get(url)
        self._check_and_handle_http_error(
            url,
            response,
            should_exit=False,
        )
        return response

    def get_package_versions(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Package/operation/listVersions
        url = self._public_api_url_to(
            what="list",
            path=get_package_purl(
                self.params.purl,
            ),
        )
        response = self._do_get(url)
        return response
