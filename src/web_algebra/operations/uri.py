from rdflib import BNode, URIRef
from rdflib.term import Node
from web_algebra.operation import Operation


class URI(Operation):
    """
    Converts any RDF term to a URI reference (like SPARQL's URI() function)
    """

    @classmethod
    def description(cls) -> str:
        return "Converts any RDF term to a URI reference (like SPARQL's URI() function)"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"description": "The input value to convert to URI"},
            },
            "required": ["input"],
        }

    def execute(self, term: Node) -> URIRef:
        """Pure function: RDFLib term → URI reference"""
        if not isinstance(term, Node):
            raise TypeError(
                f"URI operation expects input to be RDFLib term, got {type(term)}"
            )
        if isinstance(term, BNode):
            # formal-semantics.md §4.2: a blank node has no IRI to cast to.
            raise TypeError("URI cannot cast a BNode — blank nodes have no IRI")

        return URIRef(str(term))

    def execute_json(self, arguments: dict, variable_stack: list = None) -> URIRef:
        """JSON execution: processes JSON args, returns RDFLib URI reference"""
        # Process the input argument through the JSON system
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )

        # Expect RDFLib term directly
        if not isinstance(input_data, Node):
            raise TypeError(
                f"URI operation expects input to be RDFLib term, got {type(input_data)}"
            )

        # Call pure function
        return self.execute(input_data)
