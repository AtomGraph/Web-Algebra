from typing import List, Dict, Iterator
from rdflib.term import Node
from rdflib import URIRef, Literal, BNode
from rdflib.query import Result, ResultRow


class JSONResult(Result):
    """
    A SPARQL Results container that subclasses rdflib.query.Result,
    can be constructed from SPARQL JSON format and works with RDFLib objects internally.
    """

    def __init__(self, vars: List[str], bindings: List[Dict[str, Node]]):
        super().__init__("SELECT")  # Always SELECT type for our use case
        self.head = {"vars": vars}
        self.bindings = bindings
        # Set the parent class vars attribute
        self.vars = vars

    @classmethod
    def from_json(cls, json_dict: dict) -> "JSONResult":
        """Construct from SPARQL JSON format"""
        vars = json_dict["head"]["vars"]
        bindings = []

        for json_binding in json_dict["results"]["bindings"]:
            rdf_binding = {}
            for var, binding_dict in json_binding.items():
                rdf_binding[var] = cls._parse_binding(binding_dict)
            bindings.append(rdf_binding)

        return cls(vars, bindings)

    @staticmethod
    def _parse_binding(binding_dict: dict) -> Node:
        """Convert SPARQL JSON binding to RDFLib object"""
        if binding_dict["type"] == "uri":
            return URIRef(binding_dict["value"])
        elif binding_dict["type"] == "literal":
            value = binding_dict["value"]
            datatype = binding_dict.get("datatype")
            lang = binding_dict.get("xml:lang")

            if datatype:
                datatype = URIRef(datatype)

            return Literal(value, datatype=datatype, lang=lang)
        elif binding_dict["type"] == "bnode":
            return BNode(binding_dict["value"])
        else:
            raise ValueError(f"Unknown binding type: {binding_dict['type']}")

    @staticmethod
    def _serialize_binding(term: Node) -> dict:
        """Convert RDFLib object to SPARQL JSON binding"""
        if isinstance(term, URIRef):
            return {"type": "uri", "value": str(term)}
        elif isinstance(term, Literal):
            result = {"type": "literal", "value": str(term)}
            if term.datatype:
                result["datatype"] = str(term.datatype)
            if term.language:
                result["xml:lang"] = term.language
            return result
        elif isinstance(term, BNode):
            return {"type": "bnode", "value": str(term)}
        else:
            raise ValueError(f"Unknown RDFLib term type: {type(term)}")

    def to_json(self) -> dict:
        """Convert back to SPARQL JSON format"""
        json_bindings = []

        for binding in self.bindings:
            json_binding = {}
            for var, term in binding.items():
                json_binding[var] = self._serialize_binding(term)
            json_bindings.append(json_binding)

        return {"head": {"vars": self.vars}, "results": {"bindings": json_bindings}}

    def __iter__(self) -> Iterator[ResultRow]:
        """Allow iteration over bindings as ResultRow objects"""
        for binding in self.bindings:
            yield ResultRow(binding, self.vars)

    def __len__(self) -> int:
        """Number of bindings"""
        return len(self.bindings)

    def __getitem__(self, index: int) -> Dict[str, Node]:
        """Access binding by index"""
        return self.bindings[index]

    def filter_by_position(self, position: int) -> "JSONResult":
        """Filter to a single binding by 1-based position (XSLT-style)"""
        if position < 1:
            raise ValueError("Position must be >= 1 (XSLT-style 1-based indexing)")

        if position > len(self.bindings):
            raise ValueError(
                f"Position {position} exceeds number of bindings ({len(self.bindings)})"
            )

        # Convert to 0-based index and create new result with single binding
        filtered_binding = self.bindings[position - 1]
        return JSONResult(self.head["vars"], [filtered_binding])

    # Additional Result interface methods

    def __bool__(self) -> bool:
        """Return True if there are any bindings"""
        return len(self.bindings) > 0

    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if not isinstance(other, JSONResult):
            return False
        return self.head == other.head and self.bindings == other.bindings

    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return f"JSONResult(vars={self.vars}, bindings={len(self.bindings)} rows)"

    def __str__(self) -> str:
        """Pretty table representation"""
        if not self.bindings:
            return f"JSONResult: {self.vars} (0 rows)\n(empty)"

        # Calculate column widths
        col_widths = {}
        for var in self.vars:
            col_widths[var] = max(
                len(var),
                max(len(str(binding.get(var, "NULL"))) for binding in self.bindings),
            )

        # Build table
        lines = []

        # Header
        header = (
            "| " + " | ".join(var.ljust(col_widths[var]) for var in self.vars) + " |"
        )
        separator = (
            "+" + "+".join("-" * (col_widths[var] + 2) for var in self.vars) + "+"
        )

        lines.append(f"JSONResult: {self.vars} ({len(self.bindings)} rows)")
        lines.append(separator)
        lines.append(header)
        lines.append(separator)

        # Rows
        for binding in self.bindings:
            row = (
                "| "
                + " | ".join(
                    str(binding.get(var, "NULL")).ljust(col_widths[var])
                    for var in self.vars
                )
                + " |"
            )
            lines.append(row)

        lines.append(separator)

        return "\n".join(lines)
