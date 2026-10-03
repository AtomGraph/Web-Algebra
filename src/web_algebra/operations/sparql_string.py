import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, List, Optional, Type
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import Result
from mcp import types
from openai import OpenAI
from web_algebra.client import SPARQLClient
from web_algebra.client_operation import ClientOperation
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation

SYSTEM_PROMPT = (
    "You are a SPARQL expert. Convert the user's natural language question into a valid SPARQL query. "
    "When a section titled 'What the endpoint holds' follows, it is the ground truth about the data: use its terms and nothing else. "
    "Always include all necessary PREFIX declarations at the beginning of the query. "
    "Return only the raw SPARQL query string with no markdown fences, explanations, or extra text. "
    "SPARQL is evaluated inside-out: a nested SELECT subquery is evaluated in isolation before its results are joined with the outer WHERE clause. "
    "Therefore, any variable used in a FILTER or ORDER BY inside a nested SELECT MUST also be bound by a triple pattern inside that same nested SELECT."
)

# The prologue of a query: its BASE and PREFIX declarations.
_PROLOGUE = re.compile(
    r"^\s*(?:(?:BASE\s*<[^>]*>|PREFIX\s+[^\s:]*:\s*<[^>]*>)\s*)*", re.IGNORECASE
)
_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


@dataclass(frozen=True)
class Rejection:
    """Why a query goes back to the model. Fatal when the query would fail
    downstream too (it is not a query, not the declared shape, or refused by
    the endpoint); not when it merely matches nothing, since an empty answer
    can be the true one."""

    reason: str
    fatal: bool


class SPARQLString(ClientOperation, Operation, MCPTool):
    """
    Writes a SPARQL query for an endpoint from a natural-language question via
    an LLM — the algebra's `xsl:evaluate` (formal-semantics.md §4.3).
    """

    client_class: ClassVar[Type] = SPARQLClient

    #: How many times the model is asked for one query: the first answer and
    #: the corrections of it.
    MAX_ATTEMPTS: ClassVar[int] = 3
    #: What a context value is cut to in the prompt, in rows and characters.
    MAX_CONTEXT_ROWS: ClassVar[int] = 60
    MAX_CONTEXT_CHARS: ClassVar[int] = 100_000

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        self.llm = OpenAI(api_key=getattr(self.settings, "openai_api_key", None))
        self.model = getattr(self.settings, "openai_model", None)

    @classmethod
    def description(cls) -> str:
        return """
        Writes a SPARQL query for an endpoint from a natural language question, using an LLM.
        `projection` names the variables the query must project (because what follows reads them from its rows).
        `context` holds operations (e.g. a SELECT that inventories predicates, or looks a label up) whose
        results are shown to the model as what the endpoint holds, before it writes the query.
        A query that does not parse or lacks the projection goes back to the model, a few times at most.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "The SPARQL endpoint the query is for.",
                },
                "question": {
                    "type": "string",
                    "description": "The natural language question to convert into a SPARQL query.",
                },
                "projection": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Variable names the query must be a SELECT projecting.",
                },
                "context": {
                    "type": "array",
                    "description": "Operations whose results show the model what the endpoint holds.",
                },
            },
            "required": ["endpoint", "question"],
        }

    def execute(
        self,
        endpoint: URIRef,
        question: Literal,
        projection: Optional[List[Literal]] = None,
        context_values: Optional[List[Any]] = None,
    ) -> Literal:
        """Generate a query for `endpoint`; `context_values` is the evaluated
        JSON `context` argument (renamed: `context` is the operation's focus)."""
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"SPARQLString expects endpoint to be URIRef, got {type(endpoint).__name__}"
            )
        question = self.to_string_literal(question)
        variables = self._variables(projection)
        excerpt = self._context_section(context_values or [])

        messages = [
            {"role": "system", "content": self._system_prompt(str(endpoint), variables) + excerpt},
            {"role": "user", "content": str(question)},
        ]
        logging.info("Generating SPARQL query for question: %s", question)

        query = ""
        rejection: Optional[Rejection] = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            query = self._strip_fences(self._complete(messages))
            logging.info(
                "SPARQLString produced query (attempt %d/%d):\n%s",
                attempt, self.MAX_ATTEMPTS, query,
            )
            reason = self.rejection(query, variables)
            rejection = Rejection(reason, True) if reason else self._unmatched(str(endpoint), query)
            if rejection is None:
                return Literal(query)
            if attempt == self.MAX_ATTEMPTS and not rejection.fatal:
                # an empty answer can be the true one; SELECT reports it as zero rows
                logging.info("SPARQLString: the last query still matches nothing; it goes downstream")
                return Literal(query)
            logging.info("SPARQLString rejected the query: %s", rejection.reason)
            messages.append({"role": "assistant", "content": query})
            messages.append(
                {"role": "user", "content": rejection.reason + " Return the corrected query, and nothing else."}
            )

        raise ValueError(
            f'SPARQLString: after {self.MAX_ATTEMPTS} attempts the model wrote no query for "{question}": '
            f"{rejection.reason}\n{query}"
        )

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: evaluate every argument eagerly, then generate"""
        endpoint = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        question = Operation.process_json(
            self.settings, arguments["question"], self.context, variable_stack
        )
        projection = None
        if "projection" in arguments:
            projection = Operation.process_json(
                self.settings, arguments["projection"], self.context, variable_stack
            )
            if not isinstance(projection, list):
                raise TypeError(
                    f"SPARQLString expects 'projection' to be an array of names, got {type(projection).__name__}"
                )
        context_values = None
        if "context" in arguments:
            forms = arguments["context"]
            if not isinstance(forms, list):
                raise TypeError(
                    f"SPARQLString expects 'context' to be an array of forms, got {type(forms).__name__}"
                )
            # evaluated one by one, not as a sequence form: each is shown as
            # one exploration, and a Result is one value, not its rows
            context_values = [
                Operation.process_json(self.settings, form, self.context, variable_stack)
                for form in forms
            ]
        return self.execute(endpoint, question, projection, context_values)

    @staticmethod
    def _variables(projection: Optional[List[Any]]) -> List[str]:
        """The declared projection's names, without SPARQL's `?`/`$` sigil."""
        names: List[str] = []
        for name in projection or []:
            if not Operation.is_string_literal(name):
                raise TypeError(
                    f"SPARQLString expects 'projection' names to be string Literals, got {name!r}"
                )
            text = str(name).strip()
            names.append(text[1:] if text[:1] in ("?", "$") else text)
        return names

    @staticmethod
    def rejection(query: str, variables: List[str]) -> Optional[str]:
        """Why `query` is not the query asked for, as the next thing to tell
        the model, or None when it is: it must parse, and with a declared
        projection be a SELECT projecting every declared variable."""
        if not query.strip():
            return "You wrote no query."
        try:
            prepared = prepareQuery(query)
        except Exception as e:
            return f"That is not a SPARQL query: {str(e).strip()}."
        if not variables:
            return None
        declared = " ".join(f"?{v}" for v in variables)
        if prepared.algebra.name != "SelectQuery":
            return f"The query must be a SELECT projecting {declared}."
        projected = {str(var) for var in prepared.algebra.get("PV", [])}
        missing = [v for v in variables if v not in projected]
        if not missing:
            return None
        return (
            f"The query must project {declared}, named exactly so; it does not project "
            + " ".join(f"?{v}" for v in missing)
            + "."
        )

    def _unmatched(self, endpoint: str, query: str) -> Optional[Rejection]:
        """Why the endpoint would answer `query` with nothing, or None when it
        would not — or cannot say. The query's pattern is put to the endpoint
        as an ASK; a refusal (4xx) goes back to the model with the endpoint's
        reason, an answer it could not give lets the query through."""
        ask = self._ask(query)
        if ask is None:
            return None
        try:
            answer = self.client.query(endpoint, ask, post=True)
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                return Rejection(
                    f"The endpoint refused the query's pattern with HTTP {e.code}: {e.reason}. "
                    "Rewrite the query so that this endpoint accepts it, with the terms under "
                    "'What the endpoint holds' only.",
                    True,
                )
            logging.info("SPARQLString: %s answered %s to the ASK; whether the query matches is unknown", endpoint, e.code)
            return None
        except Exception as e:
            logging.info("SPARQLString: could not ask %s whether the query matches: %s", endpoint, e)
            return None
        if not isinstance(answer, dict) or answer.get("boolean") is not False:
            return None
        return Rejection(
            "The endpoint answered that the query's pattern matches nothing, so the query as written "
            "returns no rows. Rewrite it with the terms under 'What the endpoint holds' only, and loosen "
            "what you assumed about the values: a language tag, a datatype, an exact string or an "
            "identifier you did not see there.",
            False,
        )

    @staticmethod
    def _ask(query: str) -> Optional[str]:
        """A SELECT's pattern as an ASK: the SELECT becomes a subquery of an
        ASK with the same prologue, which SPARQL 1.1 allows with its solution
        modifiers and VALUES. None for other query forms, and for a SELECT
        with a dataset clause, which a subquery cannot carry."""
        try:
            prepared = prepareQuery(query)
        except Exception:
            return None
        if prepared.algebra.name != "SelectQuery" or prepared.algebra.get("datasetClause"):
            return None
        prologue = _PROLOGUE.match(query).group(0)
        ask = f"{prologue}ASK {{ {query[len(prologue):]} }}"
        try:
            prepareQuery(ask)
        except Exception:
            return None
        return ask

    def _system_prompt(self, endpoint: str, variables: List[str]) -> str:
        prompt = SYSTEM_PROMPT
        if variables:
            prompt += (
                "\n\nThe query must be a SELECT that projects the variables "
                + " ".join(f"?{v}" for v in variables)
                + ", named exactly so, since what follows reads them by name from its rows; "
                "it may project others as well."
            )
        now = datetime.now().astimezone()
        prompt += (
            f"\n\nThe current date and time is: {now.isoformat()} (timezone: {now.tzname()})."
            " When generating date literals for SPARQL, express them as xsd:dateTime values adjusted to UTC (Z suffix)."
        )
        agents_md = self._agents_md(endpoint)
        if agents_md:
            prompt += "\n\n# Service documentation:\n" + agents_md
        return prompt

    def _agents_md(self, endpoint: str) -> Optional[str]:
        """The endpoint's `AGENTS.md`, resolved against its URL, if it has one."""
        url = urllib.parse.urljoin(endpoint, "AGENTS.md")
        request = urllib.request.Request(url, headers={"Accept": "text/markdown, text/plain"})
        try:
            with self.client.opener.open(request) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            logging.debug("SPARQLString: no AGENTS.md at %s: %s", url, e)
            return None

    def _context_section(self, values: List[Any]) -> str:
        """The explorations' results, rendered for the model. An empty one is
        an error (§4.3): what it assumed does not match the endpoint."""
        if not values:
            return ""
        parts = [
            "\n\n# What the endpoint holds\n\nThe results of queries already run against this endpoint. "
            "Write the query with the terms that appear here - classes, predicates, identifiers, value shapes - "
            "and not with terms recalled from elsewhere; a term that does not appear here is one the data does not have.\n"
        ]
        for value in values:
            if self._is_empty(value):
                raise ValueError(
                    "SPARQLString: a 'context' exploration returned nothing, so the query cannot be "
                    "written from it; what it assumed - a class, a property, an identifier - does not "
                    "match the endpoint"
                )
            parts.append("\n" + self._render(value) + "\n")
        return "".join(parts)

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if isinstance(value, Result):
            return len(list(value)) == 0
        if isinstance(value, Graph):
            return len(value) == 0
        if isinstance(value, list):
            return len(value) == 0
        return value is None or not str(value).strip()

    def _render(self, value: Any) -> str:
        """A result set as its rows, a graph as Turtle, anything else as its
        string — cut to MAX_CONTEXT_ROWS rows and MAX_CONTEXT_CHARS characters."""
        if isinstance(value, Result):
            names = [str(var) for var in (value.vars or [])]
            rows = list(value)
            lines = ["\t".join(names)]
            for row in rows[: self.MAX_CONTEXT_ROWS]:
                cells = row.asdict()
                lines.append("\t".join(
                    cells[name].n3() if cells.get(name) is not None else "" for name in names
                ))
            if len(rows) > self.MAX_CONTEXT_ROWS:
                lines.append(f"... {len(rows) - self.MAX_CONTEXT_ROWS} more rows")
            text = "\n".join(lines)
        elif isinstance(value, Graph):
            text = value.serialize(format="turtle")
        else:
            text = str(value)
        if len(text) > self.MAX_CONTEXT_CHARS:
            text = text[: self.MAX_CONTEXT_CHARS] + "\n... cut\n"
        return text

    def _complete(self, messages: List[dict]) -> str:
        chat_completion = self.llm.chat.completions.create(
            model=self.model, messages=messages
        )
        return chat_completion.choices[0].message.content or ""

    @staticmethod
    def _strip_fences(text: str) -> str:
        match = _FENCE.match(text)
        return (match.group(1) if match else text).strip()

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        question = Literal(arguments["question"], datatype=XSD.string)
        projection = [Literal(name) for name in arguments.get("projection", [])]

        result = self.execute(endpoint, question, projection or None)
        return [types.TextContent(type="text", text=str(result))]
