from typing import Any, Callable, List, Optional, Union
import logging
import re
from elementpath.regex import RegexError, translate_pattern
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
    # x is not re.VERBOSE: F&O removes whitespace outside character classes
    # and gives # no meaning, so it is applied to the pattern text instead
    _FLAG_MAP = {
        "i": re.IGNORECASE,
        "s": re.DOTALL,
        "m": re.MULTILINE,
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
    def _remove_whitespace(pattern: str) -> str:
        """The x flag (F&O 3.1 §5.6.1): whitespace (#x9, #xA, #xD, #x20) is
        removed from the pattern, except within a character class expression."""
        out = []
        depth = 0
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch == "\\" and i + 1 < len(pattern):
                out.append(pattern[i : i + 2])
                i += 2
                continue
            if ch == "[":
                depth += 1
            elif ch == "]" and depth:
                depth -= 1
            if depth or ch not in "\t\n\r ":
                out.append(ch)
            i += 1
        return "".join(out)

    @staticmethod
    def _replacement_parts(replacement: str, groups: int) -> List[Union[str, int]]:
        """The replacement string per F&O 3.1 §5.6.4, as literal text and group
        numbers. `\\$` is a dollar and `\\\\` a backslash; any other `\\` is an
        error. `$N` takes every digit that follows: N=0 is the whole match,
        1<=N<=S group N, S<N<=9 the zero-length string; otherwise the last digit
        is a literal and the rule is reapplied to the rest. A `$` not followed by
        a digit is an error (err:FORX0004)."""
        parts: List[Union[str, int]] = []
        i = 0
        n = len(replacement)
        while i < n:
            ch = replacement[i]
            if ch == "\\":
                if i + 1 < n and replacement[i + 1] in "\\$":
                    parts.append(replacement[i + 1])
                    i += 2
                    continue
                raise ValueError(
                    "Replace: invalid escape in replacement string (XPath err:FORX0004)"
                )
            if ch == "$":
                j = i + 1
                while j < n and replacement[j].isdigit():
                    j += 1
                digits = replacement[i + 1 : j]
                if not digits:
                    raise ValueError(
                        "Replace: '$' must be followed by a group number in the replacement string (XPath err:FORX0004)"
                    )
                literal = ""
                number = int(digits)
                while number > groups and number > 9:
                    literal = digits[-1] + literal
                    digits = digits[:-1]
                    number = int(digits)
                if number <= groups:
                    parts.append(number)
                parts.append(literal)
                i = j
                continue
            parts.append(ch)
            i += 1
        return parts

    @staticmethod
    def _expander(parts: List[Union[str, int]]) -> Callable[[re.Match], str]:
        """re.sub replacement as a function, so nothing in the replacement is
        read by Python's own replacement syntax; an unmatched group is empty."""
        return lambda match: "".join(
            part if isinstance(part, str) else (match.group(part) or "") for part in parts
        )

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
            elif flag_char == "x":
                pass  # applied to the pattern text below
            else:
                raise ValueError(
                    f"Replace: invalid flag {flag_char!r} (XPath err:FORX0001)"
                )

        if literal_mode:
            # q: pattern and replacement are taken literally
            translated = re.escape(pattern_value)
        else:
            if "x" in flags_value:
                pattern_value = self._remove_whitespace(pattern_value)
            # an XSD regular expression (F&O 3.1 §5.6.1), translated to Python
            # re syntax: \p{..}/\i/\c escapes, class subtraction, and ^/$
            # anchored at the string's ends unless m is given
            try:
                translated = translate_pattern(pattern_value, flags=re_flags, xsd_version="1.1")
            except RegexError as e:
                raise ValueError(f"Replace: invalid regular expression: {e} (XPath err:FORX0002)") from None

        try:
            compiled = re.compile(translated, re_flags)
        except re.error as e:
            raise ValueError(f"Replace: invalid regular expression: {e} (XPath err:FORX0002)") from None
        if compiled.search(""):
            raise ValueError(
                "Replace: pattern matches a zero-length string (XPath err:FORX0003)"
            )
        parts = [replacement_value] if literal_mode else self._replacement_parts(replacement_value, compiled.groups)

        logging.info(
            "Resolving Replace arguments: input=%s, pattern=%s, replacement=%s, flags=%s",
            input_value,
            pattern_value,
            replacement_value,
            flags_value,
        )

        formatted_string = compiled.sub(self._expander(parts), input_value)

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
