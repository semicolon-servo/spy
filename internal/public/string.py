from typing import Any

class String(str):
    def __add__(self, other: Any) -> "String":
        return String(super().__add__(str(other)))

    def __radd__(self, other: Any) -> "String":
        return String(str(other) + str(self))
