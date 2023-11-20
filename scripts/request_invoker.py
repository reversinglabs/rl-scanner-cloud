import sys

from requests import Response
from requests.exceptions import HTTPError, JSONDecodeError

from request_factory import RequestFactory
from params import Params
from typing import BinaryIO

from cimessages import Messages


class RequestInvoker:
    def __init__(self, reporter: Messages, request_factory: RequestFactory = RequestFactory()) -> None:
        self.reporter = reporter
        self.request_factory = request_factory

    def scan_version(self, params: Params, file: BinaryIO) -> Response:
        try:
            response = RequestFactory().post_scan_version_request(params, file)
            response.raise_for_status()
        except HTTPError as error:
            self._handle_error(error)

    def get_performed_checks(self, params: Params) -> Response:
        try:
            response = RequestFactory().get_performed_checks_request(params)
            response.raise_for_status()

            return response
        except HTTPError as error:
            self._handle_error(error)

    def export_analysis_report(self, params: Params, report_format: str) -> Response:
        try:
            response = RequestFactory().get_export_analysis_report_request(params, report_format)
            response.raise_for_status()

            return response
        except HTTPError as error:
            self._handle_error(error, False)

    def _handle_error(self, error: HTTPError, should_exit: bool = True):
        try:
            error_message = error.response.json()
            self.reporter.info(error_message.get("error", f"Something went wrong with analysis report export {error}"))
            if should_exit:
                sys.exit(101)

        except JSONDecodeError as e:
            self.reporter.info(f"Something went wrong with your request {e}")
            if should_exit:
                sys.exit(101)
