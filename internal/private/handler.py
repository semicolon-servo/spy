from typing import Any

from ..public.safe import safe


class Handler:
    def __init__(self, args: list[str]) -> None:
        self.args: list[str] = args
    @safe
    def get(self, index_or_option: int | str, else_value: Any = None) -> str:
        """servo.internal.private.handler"""
        if isinstance(index_or_option, int):
            if index_or_option >= len(self.args):
                return else_value
            return self.args[index_or_option]
        elif isinstance(index_or_option, str):
            for index, arg in enumerate(self.args):
                if arg == index_or_option:
                    return self.args[index + 1]
            return else_value
        else:
            raise ValueError("index_or_option must be int or str")