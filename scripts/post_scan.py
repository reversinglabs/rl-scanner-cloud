import os
import time
from urllib.parse import urlparse

import requests
from cimessages import Messages
from constants import (
    ATTEMPT_TIMEOUT_SEC,
    DOWNLOAD_CHUNK_SIZE,
    GB,
    REPORT_FILE_SIZE_LIMIT,
    REPORT_FORMATS,
    REQUEST_TIMEOUT,
)
from params import Params
from portal_api import PortalAPI
from requests import Response


class PostScan:
    def __init__(
        self,
        params: Params,
        reporter: Messages,
        scanner: PortalAPI,
    ) -> None:
        self.params = params
        self.reporter = reporter
        self.scanner = scanner

    def _get_scan_status(
        self,
    ) -> str:
        portal: PortalAPI = self.scanner
        timeout: int = self.params.timeout

        attempt_timeout_sec: int = ATTEMPT_TIMEOUT_SEC
        deadline = time.monotonic() + timeout * 60
        while time.monotonic() < deadline:
            self.reporter.info("Attempting to fetch analysis status")

            response = portal.get_performed_checks()
            if response.status_code == 202:
                remaining = deadline - time.monotonic()
                time.sleep(min(attempt_timeout_sec, max(0.0, remaining)))
                continue

            try:
                j = response.json()
            except requests.exceptions.JSONDecodeError as e:
                raise ValueError("Fatal: we expected to see a json response") from e

            summary = j.get("analysis", {}).get("report", {}).get("info", {}).get("summary", {})

            s = summary.get("scan_status", None)
            if s is None:
                raise RuntimeError(f"Fatal: no proper scan_status found in the report summary: {summary}")

            return str(s)

        msg = "Preset timeout time expired"
        self.reporter.info(msg)
        raise RuntimeError(msg)

    def _get_analysis_reference(
        self,
    ) -> str:
        request_invoker: PortalAPI = self.scanner
        response = request_invoker.get_analysis_status()
        if not response.ok:
            raise RuntimeError(f"Fatal: missing analysis_url: {response.status_code} {response.text}")

        try:
            jdata = response.json()
        except requests.exceptions.JSONDecodeError as json_decode_error:
            msg = f"Something went wrong with your request cannot find 'get_analysis_status': {json_decode_error}"
            raise RuntimeError(msg) from None

        analysis_url = (
            jdata.get(
                "analysis",
                {},
            )
            .get(
                "report",
                {},
            )
            .get(
                "info",
                {},
            )
            .get(
                "portal",
                {},
            )
            .get(
                "reference",
                None,
            )
        )

        if analysis_url:
            return str(analysis_url)

        raise RuntimeError("Fatal: missing analysis_url")

    def _write_download_file(
        self,
        response: Response,
        report_path: str,
        report_filename: str,
    ) -> bool:
        total: int = 0
        dest = os.path.join(report_path, report_filename)
        source = f"{dest}.part"
        max_file_size = int(REPORT_FILE_SIZE_LIMIT / GB)

        remove_file = False
        file_too_big: bool = False
        try:
            with open(source, "wb") as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    total += len(chunk)
                    if total > REPORT_FILE_SIZE_LIMIT:
                        remove_file = True
                        file_too_big = True
                        break
                    f.write(chunk)

        except Exception as e:
            self.reporter.error(f"Error writing file {dest}: {e}")
            remove_file = True
        finally:
            response.close()

        if remove_file:
            if os.path.isfile(source):
                os.remove(source)
            if file_too_big:
                msg = f"Fatal: Report file '{source}' size is larger than {max_file_size}GB"
                raise RuntimeError(msg)
            return False

        if os.path.isfile(source):
            os.replace(source, dest)
            return True
        return False

    def _do_export_analysis_report(
        self,
    ) -> None:
        portal: PortalAPI = self.scanner
        report_formats: list[str] = self.params.report_format  # is now list and already validated
        report_path = self.params.report_path
        if report_path is None:
            raise RuntimeError("FATAL: report path is not set")

        for report_format in report_formats:
            self.reporter.info(f"Started {report_format} export")

            this_report_filename = self._get_default_report_name(report_format)
            response = portal.export_analysis_report(report_format)
            status = self._write_download_file(response, report_path, this_report_filename)
            if status:
                self.reporter.info(f"Finished {report_format} export")
            else:
                msg = f"Fatal: missing report for: {report_format}"
                raise RuntimeError(msg)

    def _do_export_pack_safe(
        self,
    ) -> None:
        portal = self.scanner
        report_path = self.params.report_path
        if report_path is None:
            raise RuntimeError("FATAL: report path is not set")

        response = portal.export_pack_safe()
        if not response.ok:
            raise RuntimeError("Fatal: no proper response: for export_pack_safe")

        data = response.json()

        # we expect only a filename not a directory or a path
        report_filename: str = data.get("file_name") or ""  # sanitize the file_name
        sane_report_filename: str = str(os.path.basename(report_filename))

        if len(sane_report_filename) == 0:
            raise RuntimeError("Fatal: illegal report file: it returns a empty path")

        if "\\" in sane_report_filename:
            raise RuntimeError(f"Fatal: illegal report file: {report_filename}")

        if sane_report_filename.startswith("."):
            raise RuntimeError(f"Fatal: illegal report file: {report_filename}")

        if sane_report_filename != report_filename:
            raise RuntimeError(f"Fatal: report_filename contains unexpected characters: '{report_filename}'")

        self.reporter.info("Started rl-safe export")

        download_url: str = data.get("download_link") or ""
        if not download_url:
            raise RuntimeError("Fatal: no download url for the pack safe report")

        valid = self._is_well_formed_download_url(
            download_url
        )  # currently no validation on the download server, some cdn.
        if valid is False:
            raise RuntimeError(f"Fatal: the download url for the pack safe report is not a valid url: {download_url}")

        response = requests.get(  # note this is not the portal api this is often a s3 interface s no session use
            download_url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            proxies=portal.proxies,
            allow_redirects=False,
        )

        if response.status_code < 200 or response.status_code >= 300:
            msg = f"Error for rl-safe export, no export {response.status_code}"
            self.reporter.error(msg)
            raise RuntimeError(msg)

        status = self._write_download_file(response, report_path, sane_report_filename)
        if status:
            self.reporter.info("Finished rl-safe export")
        else:
            msg = "Fatal: missing report for: rl_safe export"
            raise RuntimeError(msg)

    @classmethod
    def _is_well_formed_download_url(cls, url: str) -> bool:
        try:
            result = urlparse(url)
        except ValueError:
            return False

        if not result.netloc:
            return False

        if result.scheme != "https":
            return False

        return True

    @classmethod
    def _get_default_report_name(
        cls,
        report_format: str,
    ) -> str:
        # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
        if report_format in REPORT_FORMATS:
            return str(REPORT_FORMATS.get(report_format))

        raise ValueError(f"Fatal: unsupported report format; must be one of: {REPORT_FORMATS.keys()}")

    # Public
    def after_scan(
        self,
    ) -> int:
        # STATUS -----------------------------
        with self.reporter.progress_block("Fetching analysis status"):
            scan_status = self._get_scan_status()
            passed_analysis: bool = scan_status == "pass"
            self.reporter.show_scan_result(passed_analysis)

        # REPORTS ----------------------------
        with self.reporter.progress_block("Getting the report URL"):
            analysis_relative_reference = self._get_analysis_reference()
            portal_url = self.scanner.make_base_url(
                rl_portal_host=self.params.rl_portal_host,
                rl_portal_server=self.params.rl_portal_server,
            )
            report_url = f"{portal_url}/{analysis_relative_reference}"
            # self.reporter.with_prefix("message", f"ReportURL: {report_url}")
            self.reporter.with_prefix("ReportURL", f"{report_url}")

        if self.params.report_format and self.params.report_path:
            with self.reporter.progress_block("Exporting analysis report"):
                self._do_export_analysis_report()

        if self.params.pack_safe and self.params.report_path:
            with self.reporter.progress_block("Exporting rl-safe archive"):
                self._do_export_pack_safe()

        # DONE
        return 0 if passed_analysis else 1
