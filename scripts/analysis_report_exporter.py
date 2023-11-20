from params import Params
from request_invoker import RequestInvoker
from cimessages import Messages

from typing import List


class AnalysisReportExporter:
    def __init__(self, params: Params, reporter: Messages):
        self.params = params
        self.request_invoker = RequestInvoker(reporter)
        self.reporter = reporter

    def export_analysis_report(self):
        report_formats = AnalysisReportExporter.parse_report_formats(self.params.report_format)

        for report_format in report_formats:
            response = self.request_invoker.export_analysis_report(self.params, report_format)
            self.reporter.info(f"Started {report_format} export")

            report_filename = AnalysisReportExporter._get_report_name(report_format)

            with open(f"{self.params.report_path}/{report_filename}", "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
                self.reporter.info(f"Finished {report_format} export")

    @staticmethod
    def _get_report_name(report_format: str):
        # https://docs.secure.software/cli/commands/report?_highlight=report&_highlight=format#usage
        if report_format == "sarif":
            return "report.sarif.json"
        if report_format == "cyclonedx":
            return "report.cyclonedx.json"
        if report_format == "spdx":
            return "report.spdx.json"
        if report_format == "rl-json":
            return "report.rl.json"
        if report_format == "rl-checks":
            return "report.checks.json"

    @staticmethod
    def parse_report_formats(report_formats: str) -> List[str]:
        valid_report_formats = ["sarif", "cyclonedx", "spdx", "rl-json", "rl-checks"]
        parsed_report_formats = [report_format for report_format in report_formats.split(",")]

        for report_format in parsed_report_formats:
            if report_format == "all":
                return valid_report_formats

            if report_format not in valid_report_formats:
                raise RuntimeError("Invalid report format provided")

        return parsed_report_formats
