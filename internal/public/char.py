from typing import Any


class Char:
    def __init__(self, string: str, index: int, parser: "Parser", **data: Any) -> None:
        self.string: str = string
        self.index: int = index
        self.parser: "Parser" = parser
        self.data: dict[str, Any] = data