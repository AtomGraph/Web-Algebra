"""Binding restriction: give variables of a SPARQL query or update values
without replacing them (formal-semantics.md §4.3), after A. Seaborne's
Substitution note, https://afs.github.io/substitute.html.

The rule is applied to the query *text*, which is what an operation sends to
an endpoint: the text is tokenized (so nothing inside a string, IRI or comment
is touched), every brace is classified (group graph pattern, template, inline
data, or the wrapper of a subquery), and then

1. a restricted variable is renamed inside every subquery that does not
   project it;
2. only the restricted variables that occur are kept - none, and the text is
   returned as it is;
3. one that the query assigns (AS, VALUES) raises ValueError;
4. every group graph pattern gets `VALUES (...) { ... }` as its first element.

`CONSTRUCT WHERE { P }` and `DELETE WHERE { P }`, whose pattern is also their
template, are written in their long form first.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

from rdflib import Literal, URIRef
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

# characters a SPARQL IRIREF excludes: controls, space and <>"{}|^`\
_IRIREF_EXCLUDED = re.compile(r'[\x00-\x20<>"{}|^`\\]')
# SPARQL ECHAR: \t \b \n \r \f \" \\
_ECHAR = str.maketrans({"\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f", '"': '\\"', "\\": "\\\\"})


def sparql_term(node: Any) -> str:
    """A URI or Literal in SPARQL syntax: `<iri>` (refusing a character IRIREF
    excludes), or a short quoted string with every ECHAR escaped followed by
    its language tag or datatype."""
    if isinstance(node, URIRef):
        if _IRIREF_EXCLUDED.search(str(node)):
            raise ValueError(f"<{node}> is not a valid SPARQL IRI")
        return f"<{node}>"
    if isinstance(node, Literal):
        lexical = str(node).translate(_ECHAR)
        if node.language:
            return f'"{lexical}"@{node.language}'
        if node.datatype:
            return f'"{lexical}"^^{sparql_term(node.datatype)}'
        return f'"{lexical}"'
    raise TypeError(f"Cannot write {type(node).__name__} as a SPARQL term")


# --- tokens


class _Token(NamedTuple):
    kind: str  # IRI STR VAR WORD PUNCT
    text: str
    start: int
    end: int


_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>\#[^\n]*)
  | (?P<IRI><[^<>"{}|^`\\\x00-\x20]*>)
  | (?P<STR>\"\"\"(?:[^"\\]|\\.|"(?!""))*\"\"\"|'''(?:[^'\\]|\\.|'(?!''))*'''
          |"(?:[^"\\\n\r]|\\.)*"|'(?:[^'\\\n\r]|\\.)*')
  | (?P<VAR>[?$][\w·̀-ͯ‿-⁀]+)
  | (?P<WORD>[A-Za-z_][\w\-]*(?::[\w\-.%]*)?|:[\w\-.%]*)
  | (?P<PUNCT>.)
    """,
    re.VERBOSE | re.DOTALL,
)


def _tokens(text: str) -> List[_Token]:
    out = []
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind in ("ws", "comment"):
            continue
        out.append(_Token(kind, m.group(), m.start(), m.end()))
    return out


def _is(token: _Token, *words: str) -> bool:
    return token.kind == "WORD" and token.text.upper() in words


# --- structure


class _Brace(NamedTuple):
    open: int  # token index of "{"
    close: int  # token index of the matching "}"
    kind: str  # group, subquery, template, data, short (CONSTRUCT/DELETE WHERE)


def _braces(tokens: List[_Token]) -> List[_Brace]:
    """Classify every `{ ... }` of the text."""
    braces: List[_Brace] = []
    stack: List[tuple] = []  # (open index, kind)
    expect_template = expect_data = expect_short = False
    for i, t in enumerate(tokens):
        if t.kind == "WORD":
            word = t.text.upper()
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if word in ("CONSTRUCT", "DELETE") and nxt is not None and _is(nxt, "WHERE"):
                expect_short = True
            elif word in ("CONSTRUCT", "INSERT", "DELETE") and not stack:
                expect_template = True
            elif word == "VALUES":
                expect_data = True
            continue
        if t.text == "{" and t.kind == "PUNCT":
            outer = stack[-1][1] if stack else None
            if expect_data:
                kind, expect_data = "data", False
            elif outer in ("template", "data"):
                kind = outer
            elif expect_short and not stack:
                kind, expect_short = "short", False
            elif expect_template and not stack:
                kind, expect_template = "template", False
            elif i + 1 < len(tokens) and _is(tokens[i + 1], "SELECT"):
                kind = "subquery"
            else:
                kind = "group"
            stack.append((i, kind))
        elif t.text == "}" and t.kind == "PUNCT" and stack:
            j, kind = stack.pop()
            braces.append(_Brace(j, i, kind))
    if stack:
        raise ValueError("Unbalanced braces in the query")
    return sorted(braces)


def _projection(tokens: List[_Token], brace: _Brace) -> Optional[set]:
    """The variables a subquery projects, or None for SELECT *."""
    names = set()
    depth = 0
    i = brace.open + 2  # after "{ SELECT"
    while i < brace.close:
        t = tokens[i]
        if t.text == "(" and t.kind == "PUNCT":
            depth += 1
        elif t.text == ")" and t.kind == "PUNCT":
            depth -= 1
        elif depth == 0 and (t.text == "{" or _is(t, "WHERE", "FROM")):
            break
        elif depth == 0 and t.text == "*":
            return None
        elif t.kind == "VAR" and (depth == 0 or _is(tokens[i - 1], "AS")):
            names.add(t.text[1:])
        i += 1
    return names


# --- the restriction


def restrict(text: str, variables: Sequence[str], rows: Sequence[Sequence[Optional[Any]]]) -> str:
    """Restrict `variables` of the query or update `text` to `rows` (each a
    sequence of terms or None for UNDEF, in the order of `variables`)."""
    is_update = _parse(text)
    tokens = _tokens(text)
    names = [t.text[1:] for t in tokens if t.kind == "VAR"]
    braces = _braces(tokens)
    renamed: Dict[int, str] = {}  # token index -> new variable text

    # 1. renaming inside subqueries that do not project a restricted variable
    for brace in braces:  # outermost first, as sorted by opening position
        if brace.kind != "subquery":
            continue
        projected = _projection(tokens, brace)
        for v in variables:
            if projected is not None and v in projected:
                continue
            inside = [k for k in range(brace.open, brace.close) if tokens[k].kind == "VAR"
                      and k not in renamed and tokens[k].text[1:] == v]
            if projected is None and inside:
                continue  # SELECT * projects every variable its pattern mentions
            fresh = _fresh(v, names)
            names.append(fresh)
            for k in inside:
                renamed[k] = tokens[k].text[0] + fresh

    # 2. occurrence
    occurring = {tokens[k].text[1:] for k in range(len(tokens)) if tokens[k].kind == "VAR" and k not in renamed}
    columns = [i for i, v in enumerate(variables) if v in occurring]
    if not columns:
        return text
    restricted = {variables[i] for i in columns}

    # 3. assignment
    for k, t in enumerate(tokens):
        if k in renamed:
            continue
        if _is(t, "AS") and k + 1 < len(tokens) and tokens[k + 1].kind == "VAR" and k + 1 not in renamed \
                and tokens[k + 1].text[1:] in restricted:
            raise ValueError(f"The query assigns ?{tokens[k + 1].text[1:]} (AS), whose value is given")
        if _is(t, "VALUES"):
            j = k + 1
            while j < len(tokens) and tokens[j].text != "{":
                if tokens[j].kind == "VAR" and j not in renamed and tokens[j].text[1:] in restricted:
                    raise ValueError(f"The query assigns ?{tokens[j].text[1:]} (VALUES), whose value is given")
                j += 1

    # 4. the inline data, at the start of every group
    data = _values([variables[i] for i in columns], [[row[i] for i in columns] for row in rows])
    inserts: Dict[int, str] = {}  # character offset -> text to insert
    for brace in braces:
        if brace.kind in ("group", "short"):
            inserts[tokens[brace.open].end] = " " + data
        if brace.kind == "short":
            # CONSTRUCT WHERE { P } / DELETE WHERE { P } -> CONSTRUCT { P } WHERE { P }
            where = brace.open - 1
            pattern = text[tokens[brace.open].start:tokens[brace.close].end]
            inserts[tokens[where].start] = inserts.get(tokens[where].start, "") + pattern + " "

    if not any(b.kind in ("group", "short") for b in braces):
        # DESCRIBE ?x without a WHERE clause: give it an empty one to restrict,
        # before any solution modifier
        at = next((t.start for t in tokens if _is(t, "ORDER", "LIMIT", "OFFSET", "VALUES", "GROUP", "HAVING")), len(text))
        clause = f" WHERE {{ {data} }}" if at == len(text) else f"WHERE {{ {data} }} "
        inserts[at] = inserts.get(at, "") + clause

    out, last = [], 0
    edits = sorted([(tokens[k].start, tokens[k].end, new) for k, new in renamed.items()]
                   + [(offset, offset, new) for offset, new in inserts.items()])
    for start, end, new in edits:
        out.append(text[last:start])
        out.append(new)
        last = end
    out.append(text[last:])
    result = "".join(out)
    if _parse(result) != is_update:
        raise ValueError("The restricted query does not parse")
    return result


def _parse(text: str) -> bool:
    """Parse `text` as a query, or else as an update; True for an update.
    ValueError if it is neither."""
    try:
        parseQuery(text)
        return False
    except Exception:
        pass
    try:
        parseUpdate(text)
        return True
    except Exception as e:
        raise ValueError(f"Not a SPARQL query or update: {e}") from None


def _fresh(name: str, taken: List[str]) -> str:
    n = 1
    while f"{name}_{n}" in taken:
        n += 1
    return f"{name}_{n}"


def _values(variables: List[str], rows: List[List[Optional[Any]]]) -> str:
    if not rows:
        # an empty table joins to nothing; an always-false filter means the
        # same and, unlike an empty VALUES block, every processor evaluates it
        # (rdflib 7.0 fails on `VALUES (?v) { }`, and evaluates a bare
        # FILTER(false) as true)
        return "FILTER(1 = 0)"
    head = " ".join(f"?{v}" for v in variables)
    body = " ".join("(" + " ".join("UNDEF" if term is None else sparql_term(term) for term in row) + ")" for row in rows)
    return f"VALUES ({head}) {{ {body} }}"
