from typing import Callable

from .safe import safe


class ParsedMaterial:
    def __init__(self, raw_execute: Callable, parser: "Parser") -> None:
        self.raw_execute: Callable = raw_execute
        self.parser: "Parser" = parser
    def execute(self) -> str:
        if hasattr(self.parser.file, "path"):
            @lambda func: (
                safe(func, self.parser.file.getParts()[-2] + "." + self.parser.file.getBaseName().removesuffix("." + self.parser.file.getExtension()))
            )
            def call() -> None:
                self.raw_execute()
            call()
        else:
            self.raw_execute()