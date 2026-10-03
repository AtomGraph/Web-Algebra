from typing import Any, Union
from rdflib import Graph, Literal, URIRef
from web_algebra.operation import Operation


class QuerySource:
    """Mixin for SELECT, CONSTRUCT and DESCRIBE: a query runs over a dataset
    given either as `endpoint`, the URI of a SPARQL endpoint, or as `graph`, a
    `Graph` in hand (formal-semantics.md §4.3). Exactly one is given. The graph
    case is pure and local, so it never touches the client.
    """

    def resolve_source(
        self, arguments: dict, variable_stack: list
    ) -> Union[URIRef, Graph]:
        """Evaluate whichever of `endpoint`/`graph` was given: neither raises
        KeyError, both TypeError (§4.3)."""
        has_endpoint = "endpoint" in arguments
        has_graph = "graph" in arguments
        if has_endpoint and has_graph:
            raise TypeError(
                f"{self.name()} takes exactly one of 'endpoint' and 'graph', got both"
            )
        if not has_endpoint and not has_graph:
            raise KeyError("endpoint")

        if has_endpoint:
            endpoint = Operation.process_json(
                self.settings, arguments["endpoint"], self.context, variable_stack
            )
            if not isinstance(endpoint, URIRef):
                raise TypeError(
                    f"{self.name()} operation expects 'endpoint' to be URIRef, got {type(endpoint)}"
                )
            return endpoint

        data = Operation.process_json(
            self.settings, arguments["graph"], self.context, variable_stack
        )
        if not isinstance(data, (Graph, dict, list)):
            raise TypeError(
                f"{self.name()} operation expects 'graph' to be a Graph or RDF data, got {type(data)}"
            )
        # an RDF data form is parsed with no base IRI: there is no target to
        # resolve against (§2.3, §4.3)
        return Operation.to_graph(data)

    def resolve_query(self, arguments: dict, variable_stack: list) -> Literal:
        query = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not Operation.is_string_literal(query):
            raise TypeError(
                f"{self.name()} operation expects 'query' to be string Literal, got {type(query)}"
            )
        return query

    def check_source(self, source: Any, query: Any) -> None:
        """Strict type checking before any network I/O (§3.7)."""
        if not isinstance(source, (URIRef, Graph)):
            raise TypeError(
                f"{self.name()} expects its source to be an endpoint URIRef or a Graph, got {type(source).__name__}"
            )
        if not Operation.is_string_literal(query):
            raise TypeError(
                f"{self.name()} expects query to be string Literal, got {type(query).__name__}"
            )
