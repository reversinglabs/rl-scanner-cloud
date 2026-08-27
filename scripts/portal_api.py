import os
import re
import sys
from typing import (
    Any,
    BinaryIO,
)
from urllib.parse import quote

import requests
from cimessages import Messages
from constants import (
    DEFAULT_DOMAIN,
    REQUEST_TIMEOUT,
)
from helpers import validate_port
from params import Params
from requests import Response
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    HTTPError,
)
from urllib3.util import Retry


class PortalApiBase:
    def __init__(
        self,
        params: Params,
        reporter: Messages,
    ) -> None:
        self.params: Params = params
        self.reporter: Messages = reporter

        self.api_token: str = os.environ.get("RLPORTAL_ACCESS_TOKEN", "").strip()  # is mandatory
        if len(self.api_token) == 0:
            raise RuntimeError("Fatal: env_var: RLPORTAL_ACCESS_TOKEN, is mandatory but has no value")

        self.proxies: dict[str, str] = self._make_proxy_data_from_env()

        self._start_session()

    def _start_session(self) -> None:
        self.session: requests.Session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(
                {"GET"},
            ),
        )
        self.session.mount(
            "https://",
            HTTPAdapter(max_retries=retry),
        )

    @classmethod
    def _make_proxy_data_from_env(cls) -> dict[str, str]:
        proxies: dict[str, str] = {}

        # -------------------------------------------------
        # transfer all env vars for the proxy to local vars
        # if the env vars are set but no value is provided treat them as None

        proxy_server = os.environ.get("RLSECURE_PROXY_SERVER", None)
        if proxy_server is not None and len(proxy_server) == 0:
            proxy_server = None

        if proxy_server is None:
            # no proxy, dont bother with anything else
            return proxies

        proxy_port = os.environ.get("RLSECURE_PROXY_PORT", None)
        if proxy_port is not None and len(proxy_port) == 0:
            proxy_port = None

        proxy_user = os.environ.get("RLSECURE_PROXY_USER", None)
        if proxy_user is not None and len(proxy_user) == 0:
            proxy_user = None

        proxy_password = os.environ.get("RLSECURE_PROXY_PASSWORD", None)
        if proxy_password is not None and len(proxy_password) == 0:
            proxy_password = None

        # -------------------------------------------------
        if proxy_user:
            proxy_user = quote(proxy_user, safe="")

        if proxy_password:
            proxy_password = quote(proxy_password, safe="")

        if proxy_user and not proxy_password:
            raise RuntimeError("Fatal: when using a proxy_user for authentication a proxy_pass MUST be also provided")
        # ignore password and not user silently

        # we have a proxy
        host = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
        if not re.match(host, proxy_server):
            raise RuntimeError("Fatal: proxy-server must be a valid dns hostname")

        if proxy_port is None:
            raise RuntimeError("Fatal: when a proxy_server is set you also must supply a proxy_port")

        if not re.match(r"^\d{1,5}$", f"{proxy_port}"):
            raise RuntimeError("Fatal: proxy-port must be a valid number hostname")

        validate_port(proxy_port)

        auth = ""
        if proxy_user:
            auth = f"{proxy_user}:{proxy_password}@"
        tail = f"{proxy_server}:{proxy_port}"

        prox = f"http://{auth}{tail}"
        proxies = {
            "http": prox,
            "https": prox,
        }

        return proxies

    def _auth_header(
        self,
    ) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "rl-scanner-cloud",
        }

    def _check_and_handle_http_error(
        self,
        url: str,
        response: Response,
        should_exit: bool = True,
    ) -> None:

        try:
            response.raise_for_status()
        except HTTPError as http_error:
            default_msg = f"Something went wrong with request: {url}: {http_error}"
            try:
                if http_error.response is None:
                    self.reporter.error(default_msg)
                else:
                    error_message = http_error.response.json()
                    if not error_message or not isinstance(error_message, dict):
                        self.reporter.error(default_msg)
                    else:
                        msg = error_message.get("error")
                        msg = msg if isinstance(msg, str) else default_msg
                        self.reporter.error(msg)
            except requests.exceptions.JSONDecodeError as json_decode_error:
                self.reporter.error(f"Something went wrong with your request {json_decode_error}")

            if should_exit:
                raise RuntimeError(f"Fatal: request to {url} failed: {response.status_code}") from http_error

    def _do_get(
        self,
        *,
        url: str,
        q_params: dict[str, str],
        should_exit: bool = False,
        stream: bool = False,
        expected_status: set[int] | None = None,
    ) -> Response:
        if self.params.debug:
            print(f"url: {url}, q_params: {q_params}", file=sys.stderr)

        response = self.session.get(
            url,
            params=q_params,
            headers=self._auth_header(),
            proxies=self.proxies,
            timeout=REQUEST_TIMEOUT,
            stream=stream,
        )
        if expected_status is not None:
            if response.status_code in expected_status:
                return response

        self._check_and_handle_http_error(
            url,
            response,
            should_exit=should_exit,
        )
        return response

    def _do_post(
        self,
        *,
        url: str,
        q_params: dict[str, str],
        headers: dict[str, str],
        data: Any = None,
        json: Any = None,
        should_exit: bool = False,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        if self.params.debug:
            print(f"url: {url}, q_params: {q_params}", file=sys.stderr)

        response = self.session.post(
            url,
            headers=headers,
            proxies=self.proxies,
            data=data,
            json=json,
            params=q_params,  # here we have query params
            timeout=REQUEST_TIMEOUT,
            allow_redirects=allow_redirects,
            stream=stream,
        )

        if allow_redirects is False:
            if response.status_code >= 300 and response.status_code < 400:
                if should_exit:
                    raise RuntimeError(
                        f"Fatal: request to {url} failed no redirect allowed: {response.status_code}"
                    ) from None

        self._check_and_handle_http_error(
            url,
            response,
            should_exit=should_exit,
        )
        return response

    def _public_api_url_to(
        self,
        *,
        what: str,
        tail_path_with_purl: str,  # but can also contain a pre path component <report_format>/<purl>
        version: str = "v1",
    ) -> str:
        """Builds a url to the portal api for the given command in `what` url_escapes all params"""
        tail = f"api/public/{version}"

        base_url = self.make_base_url(
            rl_portal_server=self.params.rl_portal_server,
            rl_portal_host=self.params.rl_portal_host,
        )

        public_api_url = f"{base_url}/{tail}/{what}/"

        safe_org = quote(self.params.rl_portal_org, safe="")
        safe_group = quote(self.params.rl_portal_group, safe="")

        return f"{public_api_url}{safe_org}/{safe_group}/{tail_path_with_purl}"

    # Public
    @classmethod
    def make_base_url(
        cls,
        *,
        rl_portal_host: str | None = None,
        rl_portal_server: str | None = None,  # note server means tenant
        domain: str = DEFAULT_DOMAIN,
        proto: str = "https",
    ) -> str:
        # dont add the api tail, the report url is not part of the api
        if rl_portal_server in ["playground", "trial"]:  # special cases only on the default domain
            if not rl_portal_host:
                return f"{proto}://{rl_portal_server}.{domain}"

        if rl_portal_host:
            if rl_portal_server:
                return f"{proto}://{rl_portal_host}/{rl_portal_server}"  # both host and server(tenant)

            return f"{proto}://{rl_portal_host}"  # only host, no server (tenant)

        if rl_portal_server is None:
            raise RuntimeError("Fatal: portal_server cannot be empty")

        return f"{proto}://my.{domain}/{rl_portal_server}"  # now we must have a server (tenant)


# Cannot upload a reproducible build for a non-existent version.
# for a repro upload the version must already exist


class PortalAPI(PortalApiBase):
    def __init__(
        self,
        params: Params,
        reporter: Messages,
    ) -> None:
        super().__init__(params, reporter)

    def _get_package_versions(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Package/operation/listVersions
        url = self._public_api_url_to(
            what="list",
            tail_path_with_purl=self.params.purl.get_package_purl(),  # without the version or artifact
        )

        return self._do_get(
            url=url,
            q_params={},
            should_exit=False,
            stream=False,
            expected_status=set({200, 401, 404}),
        )

    def _test_has_versions(self) -> bool | None:
        response = self._get_package_versions()
        if response.status_code not in [200, 404, 401]:
            msg = (
                f"Fatal: while validating force and replace parameters: _get_package_versions(): {response.status_code}"
            )
            raise RuntimeError(msg)

        if response.status_code == 401:
            raise RuntimeError("Fatal: request was not successful because it lacks valid authentication credentials")

        if response.status_code in [404]:
            return None

        data = response.json()
        purl_version = self.params.purl.get_version()
        versions: list[Any] = data.get("versions") or []
        for version in versions:
            if version.get("version") == purl_version:
                return True
        return False

    def _start_q_params(self) -> dict[str, str]:
        q_params: dict[str, str] = {}
        if self.params.repro:
            q_params["build"] = "repro"
        return q_params

    def _make_scan_query_params(self) -> dict[str, str]:
        q_params = self._start_q_params()

        for name in ["force", "replace"]:
            if getattr(self.params, name, None):  # only True for force and replace
                q_params[name] = "true"

        for name in ["diff_with"]:
            if getattr(self.params, name, None):  # a string for diff_with
                q_params[name] = getattr(self.params, name)

        return q_params

    def _export_report(
        self,
        url: str,
    ) -> Response:
        """All reports use this to actually download the report data
        As the reports can be large we stream the data and if a report download fails we exit
        """
        q_params = self._start_q_params()

        return self._do_get(
            url=url,
            q_params=q_params,
            should_exit=True,
            stream=True,
        )

    # Public

    def transform_force_and_replace_params(self) -> None:
        # normalize repro
        if self.params.repro or self.params.purl.has_repro():
            self.params.repro = True

        # if we have no force and no replace we have nothing to change
        if self.params.force is False and self.params.replace is False:
            return

        # if we have repro we cannot have force
        if self.params.repro:
            self.params.force = False
            return

        # if we have no versions in the portal for the item (we are the first),
        #   then neither force nor replace make sense.
        r = self._test_has_versions()
        if r is None:
            self.params.force = False
            self.params.replace = False
            return

        if r:
            # if we are replaicing a current version: we dont need force:True at all
            self.params.force = False
            return

        # this version does not exist, we dont need replace, but we may need force
        self.params.replace = False
        return

    def scan_file_version(
        self,
        *,
        file_stream: BinaryIO,
        file_name: str,
    ) -> Response:
        """Scan a file by uploading it to the portal"""
        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion

        file_base: str = os.path.basename(file_name)
        safe_file_name = quote(file_base, safe="", encoding="utf-8")

        headers = self._auth_header() | {
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_file_name}",
            "Content-Type": "application/octet-stream",
        }

        q_params = self._make_scan_query_params()

        url = self._public_api_url_to(
            what="scan",
            tail_path_with_purl=self.params.purl.purl_encoded(),
        )

        return self._do_post(
            url=url,
            q_params=q_params,
            headers=headers,
            data=file_stream,
            should_exit=True,
            allow_redirects=False,
        )

    def scan_import_url_version(
        self,
        *,
        import_url: str,
    ) -> Response:
        """scan a item by using a url"""
        # https://docs.secure.software/api-reference/#tag/Version/operation/scanVersion

        headers: dict[str, str] = self._auth_header() | {
            "Content-Type": "application/json",
        }
        q_params = self._make_scan_query_params()

        post_json_data: dict[str, Any] = {
            "url": import_url,
        }

        # the following credentials are only needed if the url access needs authentication
        if self.params.bearer_token:
            post_json_data["bearer-token"] = self.params.bearer_token
        else:
            if self.params.auth_user:
                post_json_data["auth-user"] = self.params.auth_user
            if self.params.auth_pass:
                post_json_data["auth-pass"] = self.params.auth_pass

        url = self._public_api_url_to(
            what="url-import",
            tail_path_with_purl=self.params.purl.purl_encoded(),
        )

        return self._do_post(
            url=url,
            headers=headers,
            q_params=q_params,
            json=post_json_data,
            should_exit=True,
        )

    def get_performed_checks(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionChecks

        url = self._public_api_url_to(
            what="checks",
            tail_path_with_purl=self.params.purl.purl_encoded(),
        )
        q_params = self._start_q_params()

        return self._do_get(
            url=url,
            q_params=q_params,
            should_exit=True,
            stream=False,
        )

    def get_analysis_status(
        self,
    ) -> Response:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionStatus

        url = self._public_api_url_to(
            what="status",
            tail_path_with_purl=self.params.purl.purl_encoded(),
        )

        q_params = self._start_q_params()

        return self._do_get(
            url=url,
            q_params=q_params,
            should_exit=True,
            stream=False,
        )

    def export_analysis_report(
        self,
        report_format: str,
    ) -> Response:
        what = "report"
        url = self._public_api_url_to(
            what=what,
            tail_path_with_purl=f"{report_format}/{self.params.purl.purl_encoded()}",
        )
        return self._export_report(url)

    def export_pack_safe(
        self,
    ) -> Response:
        what = "pack/safe"
        url = self._public_api_url_to(
            what=what,
            tail_path_with_purl=self.params.purl.purl_encoded(),
        )
        return self._export_report(url)
