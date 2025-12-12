from typing import Callable, Generator
from sys import argv, exit as sysexit


def safe(func: Callable, file_name: str | None = None) -> Callable:
    def wrapper(*args, **kwargs):
        nonlocal file_name
        try:
            return func(*args, **kwargs)
        except Exception as error:
            error_name: str = ""
            for char in error.__class__.__name__:
                if char.isupper():
                    error_name += " "
                error_name += char.upper()
            error_name = error_name.strip().replace("ERROR", "FATAL")
            file_name = file_name or (func.__doc__ or "<unknown>").split('\n')[0].strip()
            print(f"\033[1m[servo]\033[0;91m got '{error_name}' from {func.__name__}() in '{file_name}':\n      - {error}\033[0m")
            if file_name == "servo.base" and "-v" not in argv:
                print("\033[91m      - exit with code 1\033[0m")
                sysexit(1)
            raise error
    return wrapper