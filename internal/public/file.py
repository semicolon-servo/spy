import os
import shutil

from .safe import safe


class File:
    def __init__(self, path: str, no_read: bool = False) -> None:
        self.path: str = os.path.abspath(path)
        self.content: str | None = None
        if not no_read:
            self.read()
    @safe
    def read(self) -> str:
        """servo.internal.public.file"""
        if not self.path:
            raise ValueError("read() while path still not provided to File object.")
        with open(self.path) as f:
            self.content = f.read() + " " # add one whitespace character to handle EOF
            return self.content
    @safe
    def write(self, content: str, mode: str = "w") -> None:
        """servo.internal.public.file"""
        if not self.path:
            raise ValueError("write() while path still not provided to File object.")
        with open(self.path, mode) as f:
            f.write(content)
            self.content = content
    @safe
    def getContent(self) -> str:
        """servo.internal.public.file"""
        return self.content
    @safe
    def getPath(self) -> str:
        """servo.internal.public.file"""
        return self.path
    @safe
    def getExtension(self) -> str:
        """servo.internal.public.file"""
        return self.path.split(".")[-1]
    @safe
    def getBaseName(self) -> str:
        """servo.internal.public.file"""
        return self.path.replace("\\", "/").split("/")[-1]
    @safe
    def getParts(self) -> list[str]:
        """servo.internal.public.file"""
        return self.path.replace("\\", "/").split("/")
    @safe
    def getParent(self) -> str:
        """servo.internal.public.file"""
        return "/".join(self.getParts()[:-1])
    @safe
    def getChild(self, *tree: str) -> str:
        """servo.internal.public.file"""
        return "/".join([self.path] + list(tree))
    @safe
    def getType(self) -> str | None:
        """servo.internal.public.file"""
        if os.path.isdir(self.path):
            return "dir"
        elif os.path.isfile(self.path):
            return "file"
    @safe
    def getExists(self) -> bool:
        """servo.internal.public.file"""
        return bool(self.getType())
    @safe
    def delete(self) -> bool:
        """servo.internal.public.file"""
        if self.getType() == "file":
            os.remove(self.path)
            return True
        elif self.getType() == "dir":
            shutil.rmtree(self.path)
            return True
        return False
    @safe
    def createDirectory(self) -> bool:
        """servo.internal.public.file"""
        if not self.getExists():
            os.mkdir(self.path)
            return True
        return False