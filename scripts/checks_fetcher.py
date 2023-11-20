from time import sleep
from params import Params
from cimessages import Messages
from request_invoker import RequestInvoker


ATTEMPT_TIMEOUT_SEC = 30

DEFAULT_ATTEMPT_TIMEOUT_MIN = 20
LOWER_ATTEMPT_TIMEOUT_MIN = 10
UPPER_ATTEMPT_TIMEOUT_MIN = 1440  # 24h


class ChecksFetcher:
    def __init__(self, params: Params, reporter: Messages):
        timeout = params.timeout
        if timeout not in range(LOWER_ATTEMPT_TIMEOUT_MIN, UPPER_ATTEMPT_TIMEOUT_MIN):
            timeout = DEFAULT_ATTEMPT_TIMEOUT_MIN
            reporter.info(
                f"""
                Value of timeout parameter is out of bounds ({LOWER_ATTEMPT_TIMEOUT_MIN} - {UPPER_ATTEMPT_TIMEOUT_MIN}).
                Will set it to default {DEFAULT_ATTEMPT_TIMEOUT_MIN} minutes
            """
            )

        self.number_of_attempts = (timeout * 60) // ATTEMPT_TIMEOUT_SEC
        self.request_invoker = RequestInvoker(reporter)
        self.reporter = reporter
        self.params = params

    def get_scan_status(self) -> str:
        while True:
            if self.number_of_attempts == 0:
                self.reporter.info("Preset timeout time expired")
                return "fail"

            self.reporter.info("Attempting to fetch analysis status")
            sleep(ATTEMPT_TIMEOUT_SEC)

            response = self.request_invoker.get_performed_checks(self.params)

            if response.status_code == 202:
                self.number_of_attempts -= 1
                continue

            return (
                response.json()
                .get("analysis", {})
                .get("report", {})
                .get("info", {})
                .get("summary", {})
                .get("scan_status", "fail")
            )
