from typing import Any

class Variable:
    def __init__(self, name: str, value: Any, value_type: str, children: dict[str, "Variable"], parser: "Parser") -> None:
        self.name: str = name
        self.value: Any = value
        self.value_type: str = value_type
        self.parser: "Parser" = parser

    def call(self, args: str = "") -> Any:
        if callable(self.value):
            return self.value(args)
        raise TypeError(f"Variable '{self.name}' is not callable")