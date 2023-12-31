from contextlib import contextmanager
from enum import Enum

from typing import (
    List,
    Dict,
    Any,
)


class MessageFormat(Enum):
    TEXT = "text"
    TEAMCITY = "teamcity"


class Messages:
    @classmethod
    def create(cls, name: str) -> Any:
        if name == "teamcity":
            return TeamCityMessages()
        else:
            return TextMessages()


class TextMessages(Messages):
    def block_start(self, msg: str) -> None:
        print(f"Started: {msg}", flush=True)

    def block_end(self, msg: str) -> None:
        print(f"Finished: {msg}", flush=True)

    def info(self, msg: str) -> None:
        print(f"Info: {msg}", flush=True)

    def scan_result(self, passed: bool) -> bool:
        if passed:
            print("Scan result: PASS", flush=True)
        else:
            print("Scan result: FAIL", flush=True)
        return True

    @contextmanager
    def progress_block(self, msg: str) -> Any:
        self.block_start(msg)
        yield
        self.block_end(msg)


class TeamCityMessages(Messages):
    @classmethod
    def service_message(cls, name: str, msg: Any) -> str:
        def escape(m: str) -> str:
            escape_map: Dict[str, str] = {
                "'": "|'",
                "|": "||",
                "\n": "|n",
                "\r": "|r",
                "[": "|[",
                "]": "|]",
            }
            return "".join(escape_map.get(x, x) for x in m)

        if isinstance(msg, dict):
            msg_content: List[str] = [f"{k}='{escape(v)}'" for k, v in msg.items()]
            return f"##teamcity[{name} {' '.join(msg_content)}]"
        else:
            return f"##teamcity[{name} '{escape(msg)}']"

    def block_start(self, msg: str) -> None:
        print(TeamCityMessages.service_message("progressStart", msg), flush=True)
        print(TeamCityMessages.service_message("blockOpened", {"name": msg}), flush=True)

    def block_end(self, msg: str) -> None:
        print(TeamCityMessages.service_message("blockClosed", {"name": msg}), flush=True)
        print(TeamCityMessages.service_message("progressFinish", msg), flush=True)

    def __build_problem(self, msg: str) -> None:
        print(
            TeamCityMessages.service_message("buildProblem", {"description": msg}),
            flush=True,
        )

    def __build_status(self, msg: str) -> None:
        print(TeamCityMessages.service_message("buildStatus", {"text": msg}), flush=True)

    def info(self, msg: str) -> None:
        print(TeamCityMessages.service_message("message", {"text": msg}), flush=True)

    def scan_result(self, passed: bool) -> bool:
        if passed:
            self.__build_status("Scan result: PASS")
        else:
            self.__build_problem("Scan result: FAIL")
        return False

    @contextmanager
    def progress_block(self, msg: str) -> Any:
        self.block_start(msg)
        yield
        self.block_end(msg)
