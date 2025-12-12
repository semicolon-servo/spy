from subprocess import run as system, CalledProcessError
from typing import Callable

from ..public.safe import safe


class Builtins:
    @staticmethod
    @safe
    def system(args: str) -> None:
        """servo.internal.private.builtins"""
        try:
            result: str = system(args, shell=True, capture_output=True, text=True, check=True)
            print(result.stdout)
        except CalledProcessError as err:
            raise ValueError(err.stderr)
    @staticmethod
    @safe
    def systemreturn(args: str) -> str:
        """servo.internal.private.builtins"""
        try:
            result: str = system(args, shell=True, capture_output=True, text=True, check=True)
            return result.stdout
        except CalledProcessError as err:
            raise ValueError(err.stderr)
    @staticmethod
    @safe
    def if_(condition: bool, true: Callable) -> None:
        """servo.internal.private.builtins"""
        if condition:
            true()
        else:
            false()