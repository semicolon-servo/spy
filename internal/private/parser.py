from typing import Any, Callable
import math
import re
from os import path as ospath

from ..public.char import Char
from ..public.file import File
from ..public.layer import Layer
from ..public.safe import safe
from ..public.parsedmaterial import ParsedMaterial
from ..public.variable import Variable
from .builtins import Builtins
from ..public.string import String

class ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class Parser:
    def __init__(self, file: File) -> None:
        self.file: File = file
        self.char: Char | None = None
        self.mode_stack: list[dict[str, Any]] = []
        self.sys_stack: list[Layer] = []
        self.parsed_funcs: list[Callable] = []
        self.pool: dict[str, Variable] = {
            "system": Variable(
                name="system",
                value=Builtins.system,
                value_type="func",
                children={},
                parser=self
            ),
            "systemreturn": Variable(
                name="systemreturn",
                value=Builtins.systemreturn,
                value_type="func",
                children={},
                parser=self
            ),
            "system_math": Variable(
                name="system_math",
                value=math,
                value_type="module",
                children={},
                parser=self
            ),
            "input": Variable(
                name="input",
                value=input,
                value_type="func",
                children={},
                parser=self
            )
        }

    def getLastModeStackType(self) -> str:
        if self.mode_stack:
            return self.mode_stack[-1]["type"]
        return "NULL"

    def wrap_strings(self, expr: str) -> str:
        # Simple regex to wrap string literals in String(...)
        # Handles "..." and '...'
        def repl(match):
            return f"String({match.group(0)})"
        return re.sub(r'(\"[^\"]*\"|\'[^\']*\')', repl, expr)


    @safe
    def findVariable(self, name: str) -> Variable:
        """servo.internal.private.parser"""
        if name in self.pool:
            val = self.pool[name].value
            if type(val) is str:
                return Variable(name, String(val), "string", {}, self)
            return self.pool[name]
        
        if "." in name:
            parts = name.split(".")
            if parts[0] in self.pool:
                try:
                    val = self.pool[parts[0]].value
                    for part in parts[1:]:
                        val = getattr(val, part)
                    if type(val) is str:
                         return Variable(name, String(val), "string", {}, self)
                    return Variable(name, val, "derived", {}, self)
                except AttributeError:
                    pass

        raise ValueError(f"variable '{name}' not found")

    @safe
    def parse(self) -> ParsedMaterial:
        """servo.internal.private.parser"""
        return ParsedMaterial(lambda: (self.parseSource(), self.execute())[-1], self)
    def execute(self) -> None:
        for parsed_func in self.parsed_funcs:
            parsed_func()
    def parseSource(self) -> str:
        for ichar, schar in enumerate(self.file.getContent()):
            self.char = Char(schar, ichar, self)
            self.parseChar()
        if self.mode_stack and self.mode_stack[-1]["type"] == "WAIT_BLOCK":
            self.parseWaitBlock(eof=True)
        
        if self.mode_stack:
             raise SyntaxError(f"Unexpected end of file. Unterminated mode: {self.mode_stack[-1]['type']}")
    def parseChar(self, match_value: str | None = None) -> None:
        match match_value or self.getLastModeStackType():
            case "NULL":
                self.parseNull()
            case "IDENTIFIER":
                self.parseIdentifier()
            case "CALL":
                self.parseCall()
            case "CHECK_ASSIGNMENT":
                self.parseCheckAssignment()
            case "STRING":
                self.parseString()
            case "MATH":
                self.parseMath()
            case "COMMENT":
                self.parseComment()
            case "MLCOMMENT":
                self.parseMLComment()
            case "ARTIFACT":
                self.parseArtifact()
            case "INTEGER":
                self.parseInteger()
            case "ASSIGNMENT":
                self.parseAssignment()
            case "FUNCTION_DEF":
                self.parseFunctionDef()
            case "BLOCK":
                self.parseBlock()
            case "WAIT_BLOCK":
                self.parseWaitBlock()
            case "RETURN":
                self.parseReturn()

    def parseNull(self) -> None:
        if self.char.string.isalpha() or self.char.string == "_":
            self.mode_stack.append({"type": "IDENTIFIER", "buffer": self.char.string})
        elif self.char.string in "\"'":
            self.mode_stack.append({"type": "STRING", "buffer": "", "quote": self.char.string})
        elif self.char.string.isdigit():
            self.mode_stack.append({"type": "INTEGER", "buffer": self.char.string})
        elif self.char.string == "#":
            self.mode_stack.append({"type": "COMMENT"})
        elif self.char.string == "/" and self.char.index + 1 < len(self.file.getContent()) and self.file.getContent()[self.char.index + 1] == "*":
            self.mode_stack.append({"type": "MLCOMMENT"})
        elif self.char.string == "<":
            self.mode_stack.append({"type": "ARTIFACT", "buffer": ""})
        elif self.char.string == "{":
            self.mode_stack.append({"type": "BLOCK", "buffer": "", "nesting": 0})
        elif self.char.string.isspace(): # Handle whitespace including newlines in NULL
            pass
        else:
             raise SyntaxError(f"Unexpected character: '{self.char.string}'")

    def parseIdentifier(self) -> None:
        if self.char.string.isalnum() or self.char.string in "_.":
            self.mode_stack[-1]["buffer"] += self.char.string
        elif self.char.string == "(":
            # check if it's a function def or call
             # Logic change: keywords check first?
             # But parseIdentifier builds buffer char by char.
             # We only know it's "fn" when we hit space or (.
             
            # If buffer is "fn", this is invalid usually, unless "fn("? No, fn name(...
            
            # Use buffer to check for keywords
            self.mode_stack.append({"type": "CALL", "identifier": self.mode_stack[-1]["buffer"], "buffer": ""})
            self.mode_stack.pop(-2)
        elif self.char.string.isspace():
             if self.mode_stack[-1]["buffer"] == "fn":
                 self.mode_stack.pop() # remove IDENTIFIER
                 self.mode_stack.append({"type": "FUNCTION_DEF", "phase": "name", "name": "", "args": [], "buffer": ""})
             elif self.mode_stack[-1]["buffer"] == "return":
                 self.mode_stack.pop() # remove IDENTIFIER
                 self.mode_stack.append({"type": "RETURN", "buffer": ""})
             else:
                 self.mode_stack[-1]["type"] = "CHECK_ASSIGNMENT"
        elif self.char.string == "=":
             # Assignment directly (no space)
             var_name = self.mode_stack[-1]["buffer"].strip()
             self.mode_stack.pop() # remove IDENTIFIER
             self.mode_stack.append({"type": "ASSIGNMENT", "name": var_name, "buffer": ""})
        else:
             # End of identifier, likely just a variable access if in an expression, but here parseIdentifier is usually top level or start of something
             # If we are just popping, we lose the buffer.
             # If this is top level, and we hit space, it might be ignored?
             # existing parser just pops.
            self.mode_stack.pop()


    def parseCheckAssignment(self) -> None:
        if self.char.string.isspace() and self.char.string != "\n":
            return
        elif self.char.string == "=":
            self.mode_stack[-1]["type"] = "ASSIGNMENT"
            self.mode_stack[-1]["name"] = self.mode_stack[-1]["buffer"].strip()
            self.mode_stack[-1]["buffer"] = ""
        elif self.char.string == "\n":
            raise SyntaxError(f"Unexpected token/newline after identifier '{self.mode_stack[-1]['buffer']}'")
        else:
            raise SyntaxError(f"Unexpected token '{self.char.string}' after identifier")

    def parseInteger(self) -> None:
        if self.char.string.isdigit():
            self.mode_stack[-1]["buffer"] += self.char.string
        elif self.char.string in "+-*/%^":
            self.mode_stack[-1]["type"] = "MATH"
            self.mode_stack[-1]["buffer"] += self.char.string
        elif self.char.string == ")":
             # End of integer in a call? or just end of int
             # If we are in CALL, we need to return control.
             # existing parser pop() handles it by going back to parent
             self.mode_stack.pop()
             # We should NOT parseChar again if it's ')' as it might be consumed by parent?
             # existing parser: self.parseChar()
             # If we call parseChar(), it will be processed by parent.
             self.parseChar()
        else:
            self.mode_stack.pop()
            self.parseChar()

    def parseAssignment(self) -> None:
        if self.char.string == "\n":
            expression = self.mode_stack[-1]["buffer"].strip()
            var_name = self.mode_stack[-1]["name"]
            self.mode_stack.pop()
            
            if expression:
                scope = {n: v.value for n, v in self.pool.items()}
                scope["String"] = String
                try:
                    expression = self.wrap_strings(expression)
                    val = eval(expression, {}, scope)
                    if type(val) is str:
                        val = String(val)
                    self.pool[var_name] = Variable(var_name, val, type(val).__name__, {}, self)
                except Exception as e:
                    # print(f"Assignment error: {e}") 
                    pass
        else:
            self.mode_stack[-1]["buffer"] += self.char.string

    def parseFunctionDef(self) -> None:
        mode = self.mode_stack[-1]
        char = self.char.string
        phase = mode["phase"]

        if phase == "name":
            if char == "(":
                mode["name"] = mode["buffer"].strip()
                mode["buffer"] = ""
                mode["phase"] = "args"
            elif char.strip():
                mode["buffer"] += char
        elif phase == "args":
            if char == ")":
                 args_str = mode["buffer"]
                 raw_args = [a.strip() for a in args_str.split(",") if a.strip()]
                 mode["args"] = raw_args
                 mode["buffer"] = ""
                 mode["phase"] = "before_body"
            else:
                 mode["buffer"] += char
        elif phase == "before_body":
             if char == "{":
                 mode["phase"] = "body"
                 mode["nesting"] = 1
                 mode["buffer"] = ""
        elif phase == "body":
             if char == "{":
                 mode["nesting"] += 1
                 mode["buffer"] += char
             elif char == "}":
                 mode["nesting"] -= 1
                 if mode["nesting"] == 0:
                     self.defineFunction(mode["name"], mode["args"], mode["buffer"])
                     self.mode_stack.pop()
                 else:
                     mode["buffer"] += char
             else:
                 mode["buffer"] += char

    def defineFunction(self, name: str, args: list[str], body: str) -> None:
        clean_args = []
        block_arg_index = -1
        for i, arg in enumerate(args):
            if arg.startswith("{") and arg.endswith("}"):
                if block_arg_index != -1:
                    raise ValueError("multiple block arguments not supported")
                clean_args.append(arg[1:-1])
                block_arg_index = i
            else:
                clean_args.append(arg)

        def func_impl(*call_args: Any) -> Any:
            actual_args = []
            if len(call_args) == 1 and isinstance(call_args[0], tuple):
                actual_args = list(call_args[0])
            else:
                actual_args = list(call_args)
            
            if len(actual_args) == 1 and actual_args[0] == "":
                 actual_args = []
            for i in range(len(actual_args)):
                if type(actual_args[i]) is str:
                    actual_args[i] = String(actual_args[i])
            
            # Simple fix for VirtualFile
            class VirtualFile(File):
                def __init__(self, c): self.c = c
                def getContent(self): return self.c
            
            func_parser = Parser(VirtualFile(body))
            func_parser.pool = self.pool.copy()
            for i, arg_name in enumerate(clean_args):
                if i < len(actual_args):
                    func_parser.pool[arg_name] = Variable(arg_name, actual_args[i], "arg", {}, func_parser)
            try:
                return func_parser.parse().execute()
            except ReturnSignal as rs:
                return rs.value
        
        func_impl.block_arg_index = block_arg_index # type: ignore
        self.pool[name] = Variable(name, func_impl, "func", {}, self)

    def parseBlock(self) -> None:
        mode = self.mode_stack[-1]
        char = self.char.string
        
        if char == "{":
            mode["nesting"] += 1
            mode["buffer"] += char
        elif char == "}":
            mode["nesting"] -= 1
            if mode["nesting"] == 0:
                block_code = mode["buffer"]
                self.mode_stack.pop()
                
                # Create lambda
                anon_name = f"__lambda_{len(self.pool)}"
                self.defineFunction(anon_name, [], block_code)
                
                # Check parent
                if self.mode_stack:
                    parent = self.mode_stack[-1]
                    if "buffer" in parent:
                         parent["buffer"] += anon_name
            else:
                mode["buffer"] += char
        else:
            mode["buffer"] += char

    def parseWaitBlock(self, eof: bool = False) -> None:
        mode = self.mode_stack[-1]
        
        # If we have a buffer (lambda name populated by BLOCK), execute
        if mode["buffer"]:
            run_args = mode["run_args"]
            block_idx = mode["func"].value.block_arg_index
            
            final_args = []
            if isinstance(run_args, tuple):
                final_args = list(run_args)
            elif run_args is not None and run_args != "":
                final_args = [run_args]
            
            # Insert lambda at correct position
            # Make sure list is long enough
            while len(final_args) < block_idx:
                final_args.append(None)
            
            # If we need to insert
            if len(final_args) == block_idx:
                 final_args.append(self.findVariable(mode["buffer"]).value)
            else:
                 # Override or insert?
                 # If user provided something, we might override it or fail.
                 # Assuming insert strictly at index for now.
                 final_args.insert(block_idx, self.findVariable(mode["buffer"]).value)
                 
            self.mode_stack.pop()
            mode["func"].call(tuple(final_args))
            
            # Process current char again since we are done with WAIT_BLOCK
            if not eof:
                self.parseChar()
            return

        if not eof and self.char.string.isspace():
            return
            
        if not eof and self.char.string == "{":
            self.mode_stack.append({"type": "BLOCK", "buffer": "", "nesting": 1})
            return
            
        # Any other char means no block provided (or passed inline), execute immediately
        self.mode_stack.pop()
        mode["func"].call(mode["run_args"])
        if not eof:
            self.parseChar()
            
    def parseReturn(self) -> None:
        if self.char.string == "\n":
            buffer = self.mode_stack[-1]["buffer"]
            self.mode_stack.pop()
            val = None
            if buffer.strip():
                 scope = {n: v.value for n, v in self.pool.items()}
                 try:
                     buffer = self.wrap_strings(buffer)
                     val = eval(buffer, {}, scope)
                 except Exception as e:
                     raise ValueError(f"Return evaluation error: {e}")
            raise ReturnSignal(val)
        else:
             self.mode_stack[-1]["buffer"] += self.char.string
    def parseCall(self) -> None:
        mode = self.mode_stack[-1]
        char = self.char.string

        if char == "{":
            self.mode_stack.append({"type": "BLOCK", "buffer": "", "nesting": 1})
            return

        if mode.get("quote"):
            mode["buffer"] += char
            if char == mode["quote"]:
                mode["quote"] = None
            return

        if char in "'\"":
            mode["quote"] = char
            mode["buffer"] += char
            return

        if char == "(":
            mode["nesting"] = mode.get("nesting", 0) + 1
            mode["buffer"] += char
        elif char == ")":
            if mode.get("nesting", 0) > 0:
                mode["nesting"] -= 1
                mode["buffer"] += char
            else:
                identifier = mode["identifier"]
                arg_str = mode["buffer"]
                self.mode_stack.pop()
                
                val = arg_str
                if arg_str.strip():
                    scope = {n: v.value for n, v in self.pool.items()}
                    scope["String"] = String
                    try:
                        arg_str = self.wrap_strings(arg_str)
                        val = eval(arg_str, {}, scope)
                    except SyntaxError:
                        raise
                    except Exception as e:
                        # print(f"DEBUG: Eval failed for '{arg_str}': {e}")
                        pass
                
                
                var = self.findVariable(identifier)
                if var.value_type == "func" and getattr(var.value, "block_arg_index", -1) != -1:
                     self.mode_stack.append({"type": "WAIT_BLOCK", "func": var, "run_args": val, "buffer": ""})
                else:
                     var.call(val)
        else:
            mode["buffer"] += char

    def parseString(self) -> None:
        if self.char.string == self.mode_stack[-1]["quote"]:
            self.mode_stack.pop()
        else:
            self.mode_stack[-1]["buffer"] += self.char.string

    def parseMath(self) -> None:
        if self.char.isdigit() or self.char.string in "+-*/%^":
            self.mode_stack[-1]["buffer"] += self.char.string
        else:
            self.mode_stack.pop()
            evaluated: int | float = eval(self.mode_stack[-1]["buffer"])
            self.mode_stack[-1]["buffer"] = str(evaluated)
            self.parseChar()

    def parseComment(self) -> None:
        if self.char.string == "\n":
            self.mode_stack.pop()

    def parseMLComment(self) -> None:
        buffer = self.mode_stack[-1].get("check_buffer", "")
        if self.char.string == "*" and not buffer:
            self.mode_stack[-1]["check_buffer"] = "*"
        elif self.char.string == "/" and buffer == "*":
            self.mode_stack.pop()
        else:
            self.mode_stack[-1]["check_buffer"] = ""

    def parseArtifact(self) -> None:
        if self.char.string == ">":
            if self.mode_stack[-1]["buffer"].split()[0] == "import":
                path: str = ""
                if ospath.exists(f"{self.mode_stack[-1]['buffer'].split()[1]}.sv"):
                    path = f"{self.mode_stack[-1]['buffer'].split()[1]}.sv"
                elif ospath.exists(f"{ospath.dirname(__file__)}/../../reach/{self.mode_stack[-1]['buffer'].split()[1]}.sv"):
                    path = f"{ospath.dirname(__file__)}/../../reach/{self.mode_stack[-1]['buffer'].split()[1]}.sv"
                else:
                    raise ModuleNotFoundError(f"module '{self.mode_stack[-1]['buffer'].split()[1]}' not found locally or in reach.")
                module_parser: Parser = Parser(File(path))
                parsed: ParsedMaterial = module_parser.parse()
                parsed.execute()
                
                # Namespace logic
                class Module: pass
                mod = Module()
                defaults = Parser(File("dummy", no_read=True)).pool.keys()
                for name, var in module_parser.pool.items():
                    if name not in defaults:
                        setattr(mod, name, var.value)
                
                module_name = self.mode_stack[-1]['buffer'].split()[1]
                self.pool[module_name] = Variable(module_name, mod, "module", {}, self)
            else:
                raise ValueError(f"unknown artifact '{self.mode_stack[-1]['buffer'].split()[0]}'")
            self.mode_stack.pop()
        else:
            self.mode_stack[-1]["buffer"] += self.char.string