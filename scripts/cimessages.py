from __future__ import annotations

import abc
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum


class MessageFormat(Enum):
    TEXT = "text"
    TEAMCITY = "teamcity"

    def __str__(self) -> str:
        return self.value


class Messages(abc.ABC):
    @classmethod
    def create(
        cls,
        name: str,
    ) -> Messages:
        if name not in ["teamcity", "text"]:
            raise ValueError(f"Fatal: unknown type: {name}")

        # factory: creates a class and returns it
        if name == "teamcity":
            return TeamCityMessages()
        return TextMessages()

    @abc.abstractmethod
    def block_start(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    def block_end(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    def info(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    def error(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    def with_prefix(self, prefix: str, msg: str) -> None:
        pass

    @abc.abstractmethod
    def show_scan_result(
        self,
        passed: bool | None,
    ) -> None:
        pass

    @contextmanager
    def progress_block(self, msg: str) -> Iterator[None]:
        self.block_start(msg)
        try:
            yield
        finally:
            self.block_end(msg)


class TextMessages(Messages):
    @classmethod
    def _format_line(
        cls,
        msg: dict[str, str] | str,
    ) -> str:
        def _escape(m: str) -> str:
            escape_map: dict[str, str] = {
                "\n": " ",
                "\r": " ",
            }
            return "".join(escape_map.get(x, x) for x in m)

        if isinstance(msg, dict):
            msg_content: list[str] = [f"{k}='{_escape(v)}'" for k, v in msg.items()]
            return " ".join(msg_content)
        return _escape(msg)

    def block_start(
        self,
        msg: str,
    ) -> None:
        print(f"Started: {self._format_line(msg)}", flush=True)

    def block_end(
        self,
        msg: str,
    ) -> None:
        print(f"Finished: {self._format_line(msg)}", flush=True)

    def info(
        self,
        msg: str,
    ) -> None:
        print(f"Info: {self._format_line(msg)}", flush=True)

    def error(
        self,
        msg: str,
    ) -> None:
        print(f"Error: {self._format_line(msg)}", flush=True)

    def with_prefix(
        self,
        prefix: str,
        msg: str,
    ) -> None:
        print(f"{prefix}: {self._format_line(msg)}", flush=True)

    def show_scan_result(
        self,
        passed: bool | None,
    ) -> None:
        if passed is None:
            print("Scan result: NONE", flush=True)
            return

        if passed:
            print("Scan result: PASS", flush=True)
            return

        print("Scan result: FAIL", flush=True)


class TeamCityMessages(Messages):
    @classmethod
    def _format_service_message(
        cls,
        name: str,
        msg: dict[str, str] | str,
    ) -> str:
        def _escape(m: str) -> str:
            escape_map: dict[str, str] = {
                "'": "|'",
                "|": "||",
                "\n": "|n",
                "\r": "|r",
                "[": "|[",
                "]": "|]",
            }
            return "".join(escape_map.get(x, x) for x in m)

        if isinstance(msg, dict):
            msg_content: list[str] = [f"{k}='{_escape(v)}'" for k, v in msg.items()]
            return f"##teamcity[{name} {' '.join(msg_content)}]"

        return f"##teamcity[{name} '{_escape(msg)}']"

    def __build_problem(
        self,
        msg: str,
    ) -> None:
        print(
            self._format_service_message("buildProblem", {"description": msg}),
            flush=True,
        )

    def __build_status(
        self,
        msg: str,
    ) -> None:
        print(self._format_service_message("buildStatus", {"text": msg}), flush=True)

    def block_start(
        self,
        msg: str,
    ) -> None:
        print(self._format_service_message("progressStart", msg), flush=True)
        print(self._format_service_message("blockOpened", {"name": msg}), flush=True)

    def block_end(
        self,
        msg: str,
    ) -> None:
        print(self._format_service_message("blockClosed", {"name": msg}), flush=True)
        print(self._format_service_message("progressFinish", msg), flush=True)

    def info(
        self,
        msg: str,
    ) -> None:
        print(self._format_service_message("message", {"text": msg}), flush=True)

    def error(
        self,
        msg: str,
    ) -> None:
        print(self._format_service_message("message", {"text": msg, "status": "ERROR"}), flush=True)

    def with_prefix(
        self,
        prefix: str,
        msg: str,
    ) -> None:
        print(self._format_service_message(prefix, msg), flush=True)

    def show_scan_result(
        self,
        passed: bool | None,
    ) -> None:
        if passed is None:
            self.__build_status("Scan result: NONE")
            return

        if passed:
            self.__build_status("Scan result: PASS")
            return

        self.__build_problem("Scan result: FAIL")
