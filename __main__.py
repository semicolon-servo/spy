from sys import argv
from .internal.private.handler import Handler
from .internal.private.parser import Parser
from .internal.public.file import File
from .internal.public.safe import safe
from .internal.public.parsedmaterial import ParsedMaterial

@safe
def initServo() -> None:
    """servo.base"""
    handler: Handler = Handler(argv[1:])
    parser: Parser = Parser(File((handler.get("-m").replace(".", "/") + ".sv") if handler.get("-m") else handler.get(0), no_read=True))
    if not parser.file.path:
        raise RuntimeError("please provide a servo file as argument 1.")
    if parser.file.getType() != "file":
        raise FileNotFoundError(f"tried to run servo file that is a directory or does not exist:\n        - {parser.file.getPath()}")
    parser.file.read()
    parsed: ParsedMaterial = parser.parse()
    parsed.execute()

initServo()