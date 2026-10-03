from typing import Any, Optional
import logging
import re
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class Replace(Operation, MCPTool):
    """
    Regular-expression replacement, per SPARQL 1.1 REPLACE() / XPath
    fn:replace: `string literal REPLACE(string literal arg, simple literal
    pattern, simple literal replacement [, simple literal flags])`.
    """

    @classmethod
    def description(cls) -> str:
        return """Replaces occurrences of a regular-expression pattern in an input string, per SPARQL's REPLACE() / XPath fn:replace. The replacement string may reference capture groups as $1, $2, ...; flags `s`, `m`, `i`, `x`, `q` are supported. The result is a string literal of the same kind (datatype/language tag) as the input.

        Note: this function should not be used to build URIs! That should be done using EncodeForURI()/ResolveURI().
        """

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input string to process",
                },
                "pattern": {
                    "type": "string",
                    "description": "The regular expression to be replaced (XPath fn:replace syntax)",
                },
                "replacement": {
                    "type": "string",
                    "description": "The replacement string; $1, $2, ... reference capture groups",
                },
                "flags": {
                    "type": "string",
                    "description": "Optional XPath regex flags: any of s, m, i, x, q",
                },
            },
            "required": ["input", "pattern", "replacement"],
        }

    # XPath flag → Python re flag (formal-semantics.md §4.2); `q` is handled
    # separately (treat pattern and replacement as literal strings).
    _FLAG_MAP = {
        "i": re.IGNORECASE,
        "s": re.DOTALL,
        "m": re.MULTILINE,
        "x": re.VERBOSE,
    }

    @staticmethod
    def _is_string_compatible(lit: Any) -> bool:
        # SPARQL string literal: xsd:string, rdf:langString, or plain literal
        return isinstance(lit, Literal) and (
            lit.datatype == XSD.string
            or (lit.datatype is None and lit.language is not None)
            or (lit.datatype is None and lit.language is None)
        )

    @staticmethod
    def _is_simple(lit: Any) -> bool:
        # SPARQL simple literal (xsd:string accepted per RDF 1.1)
        return Operation.is_string_literal(lit)

    @staticmethod
    def _translate_replacement(replacement: str) -> str:
        """Translate an XPath fn:replace replacement string into Python
        `re.sub` syntax: `$N` → `\\g<N>`, `\\$` → `$`, `\\\\` → literal
        backslash. Any other use of `\\` or `$` is an error (err:FORX0004).
        """
        out = []
        i = 0
        n = len(replacement)
        while i < n:
            ch = replacement[i]
            if ch == "\\":
                if i + 1 < n and replacement[i + 1] == "\\":
                    out.append("\\\\")
                    i += 2
                    continue
                if i + 1 < n and replacement[i + 1] == "$":
                    out.append("$")
                    i += 2
                    continue
                raise ValueError(
                    "Replace: invalid escape in replacement string (XPath err:FORX0004)"
                )
            if ch == "$":
                j = i + 1
                while j < n and replacement[j].isdigit():
                    j += 1
                if j == i + 1:
                    raise ValueError(
                        "Replace: '$' must be followed by a group number in the replacement string (XPath err:FORX0004)"
                    )
                out.append(f"\\g<{replacement[i + 1:j]}>")
                i = j
                continue
            out.append(ch)
            i += 1
        return "".join(out)

    def execute(
        self,
        input_str: Literal,
        pattern: Literal,
        replacement: Literal,
        flags: Optional[Literal] = None,
    ) -> Literal:
        """Pure function: replace pattern in string with RDFLib terms"""
        if not self._is_string_compatible(input_str):
            raise TypeError(
                f"Replace expects input to be a string literal, got {type(input_str)} with datatype {getattr(input_str, 'datatype', None)}"
            )
        # Per the REPLACE signature, pattern/replacement/flags are simple
        # literals — a language-tagged value is a type error.
        for name, lit in (("pattern", pattern), ("replacement", replacement)):
            if not self._is_simple(lit):
                raise TypeError(
                    f"Replace expects {name} to be a simple literal, got {lit!r}"
                )
        if flags is not None and not self._is_simple(flags):
            raise TypeError(f"Replace expects flags to be a simple literal, got {flags!r}")

        input_value = str(input_str)
        pattern_value = str(pattern)
        replacement_value = str(replacement)
        flags_value = str(flags) if flags is not None else ""

        re_flags = 0
        literal_mode = False
        for flag_char in flags_value:
            if flag_char == "q":
                literal_mode = True
            elif flag_char in self._FLAG_MAP:
                re_flags |= self._FLAG_MAP[flag_char]
            else:
                raise ValueError(
                    f"Replace: invalid flag {flag_char!r} (XPath err:FORX0001)"
                )

        if literal_mode:
            # q: pattern and replacement are taken literally
            pattern_value = re.escape(pattern_value)
            replacement_re = replacement_value.replace("\\", "\\\\")
        else:
            replacement_re = self._translate_replacement(replacement_value)

        try:
            compiled = re.compile(pattern_value, re_flags)
        except re.error as e:
            raise ValueError(f"Replace: invalid regular expression: {e} (XPath err:FORX0002)") from None
        if compiled.search(""):
            raise ValueError(
                "Replace: pattern matches a zero-length string (XPath err:FORX0003)"
            )

        logging.info(
            "Resolving Replace arguments: input=%s, pattern=%s, replacement=%s, flags=%s",
            input_value,
            pattern_value,
            replacement_value,
            flags_value,
        )

        try:
            formatted_string = compiled.sub(replacement_re, input_value)
        except re.error as e:
            raise ValueError(f"Replace: invalid replacement string: {e} (XPath err:FORX0004)") from None

        logging.info("Formatted result: %s", formatted_string)
        # SPARQL string-function convention: the result is a string literal
        # of the same kind as the first argument.
        if input_str.language is not None:
            return Literal(formatted_string, lang=input_str.language)
        return Literal(formatted_string, datatype=input_str.datatype)

    def execute_json(
        self, arguments: dict, variable_stack: list = None
    ) -> Literal:
        """JSON execution: process arguments with strict type checking"""
        # Process input - allow implicit string conversion
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )
        input_literal = self.to_string_literal(input_data)

        # Process pattern - allow implicit string conversion
        pattern_data = Operation.process_json(
            self.settings, arguments["pattern"], self.context, variable_stack
        )
        pattern_literal = self.to_string_literal(pattern_data)

        # Process replacement - allow implicit string conversion
        replacement_data = Operation.process_json(
            self.settings, arguments["replacement"], self.context, variable_stack
        )
        replacement_literal = self.to_string_literal(replacement_data)

        flags_literal = None
        if "flags" in arguments:
            flags_data = Operation.process_json(
                self.settings, arguments["flags"], self.context, variable_stack
            )
            flags_literal = self.to_string_literal(flags_data)

        return self.execute(
            input_literal, pattern_literal, replacement_literal, flags_literal
        )

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        input_str = Literal(arguments["input"], datatype=XSD.string)
        pattern = Literal(arguments["pattern"], datatype=XSD.string)
        replacement = Literal(arguments["replacement"], datatype=XSD.string)
        flags = (
            Literal(arguments["flags"], datatype=XSD.string)
            if "flags" in arguments
            else None
        )

        result = self.execute(input_str, pattern, replacement, flags)

        return [types.TextContent(type="text", text=str(result))]
