from .safe import safe

class Layer:
    def __init__(self, name: str, layer_type: str, parser: "Parser") -> None:
        self.name: str = name
        self.type: str = layer_type
        self.parser: "Parser" = parser
        self.index: int = len(parser.stack) - 1
    @safe
    def getAbove(self) -> "Layer":
        """servo.internal.public.layer"""
        return self.parser.stack[self.index - 1]
    @safe
    def getBelow(self) -> "Layer":
        """servo.internal.public.layer"""
        return self.parser.stack[self.index + 1]