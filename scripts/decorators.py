from typing import Any


def singleton(cls: Any) -> Any:
    instances = {}

    def getinstance() -> Any:
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]

    return getinstance
