from abc import ABC, abstractmethod
import logging
from typing import Type, Dict, Optional, Any, List, ClassVar, Union
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
from rdflib.term import Node
from rdflib import URIRef, Literal, BNode, Graph
from rdflib.namespace import XSD
from rdflib.query import Result


class Operation(ABC, BaseModel):
    """
    Abstract base class for all operations with dual execution paths:
    1. execute() - Pure RDFLib function
    2. execute_json() - JSON argument processing

    Operations can optionally implement MCPTool interface for MCP client access.
    """

    registry: ClassVar[Dict[str, Type["Operation"]]] = {}
    settings: BaseSettings = Field(exclude=True)
    context: Any = {}

    model_config = ConfigDict(extra="allow")

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    @abstractmethod
    def description(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def inputSchema(cls) -> dict:
        pass

    @abstractmethod
    def execute(self, *args) -> Union[Node, Result, Graph]:
        """Pure function: RDFLib terms → RDFLib terms/Results/Graphs"""
        pass

    @abstractmethod
    def execute_json(
        self, arguments: dict, variable_stack: list = []
    ) -> Union[Node, Result, Graph]:
        """JSON execution: processes JSON args, returns RDFLib objects"""
        pass

    @classmethod
    def register(cls, operation_cls: Type["Operation"]) -> None:
        if not issubclass(operation_cls, cls):
            raise ValueError(
                f"Cannot register {operation_cls}: Must be a subclass of Operation."
            )
        cls.registry[operation_cls.name()] = operation_cls
        logging.info(f"Registered operation: {operation_cls.name()}")

    @classmethod
    def list_operations(cls) -> List[Type["Operation"]]:
        return list(cls.registry.values())

    @classmethod
    def get(cls, name: str) -> Optional[Type["Operation"]]:
        return cls.registry.get(name)

    @classmethod
    def process_json(
        cls,
        settings: BaseSettings,
        json_data: Any,
        context: dict = {},
        variable_stack: list = [],
    ) -> Any:
        """Class method for processing JSON with @op structures"""
        if isinstance(json_data, dict):
            if "@op" in json_data:
                op_name = json_data["@op"]
                op_args = json_data.get("args", {})

                operation_cls = cls.get(op_name)
                if not operation_cls:
                    raise ValueError(f"Unknown operation: {op_name}")

                operation = operation_cls(settings=settings, context=context)
                result = operation.execute_json(op_args, variable_stack)

                # Return RDFLib objects as-is for operation chaining
                return result

            # 🔁 Recurse into each value — allows nested @op inside JSON-LD and SPARQL bindings
            return {
                k: cls.process_json(settings, v, context, variable_stack)
                for k, v in json_data.items()
            }

        elif isinstance(json_data, list):
            # For sequential operations, share variable stack to allow accumulation
            results = []
            current_stack = variable_stack.copy()
            for item in json_data:
                result = cls.process_json(settings, item, context, current_stack)
                results.append(result)
            return results

        else:
            # Convert plain values to RDFLib terms
            return cls.json_to_rdflib(json_data)

    @staticmethod
    def _serialize_for_json_context(obj) -> Any:
        """Convert RDFLib objects to appropriate format for JSON consumption"""
        if isinstance(obj, (URIRef, Literal, BNode)):
            return str(obj)  # Convert RDFLib terms to strings for JSON-LD
        elif hasattr(obj, "to_json") and callable(obj.to_json):
            return obj.to_json()  # Convert Result to SPARQL JSON format
        elif isinstance(obj, Graph):
            # Keep graphs as-is for now - they'll be serialized by HTTP operations
            return obj
        else:
            return obj

    # Variable stack management methods
    def push_variable_scope(self, variable_stack: list):
        """Create a new variable scope (like entering a new XSLT template)."""
        variable_stack.append({})

    def pop_variable_scope(self, variable_stack: list):
        """Exit the current variable scope (like leaving an XSLT template)."""
        if variable_stack:
            variable_stack.pop()

    def set_variable(self, name: str, value: Any, variable_stack: list):
        """Set a variable in the current scope."""
        if not variable_stack:
            variable_stack.append({})
        variable_stack[-1][name] = value

    def get_variable(self, name: str, variable_stack: list) -> Any:
        """Get a variable value, searching from innermost to outermost scope."""
        for scope in reversed(variable_stack):
            if name in scope:
                return scope[name]
        raise ValueError(f"Variable '{name}' not found")

    # Conversion helpers between different formats
    @staticmethod
    def json_to_rdflib(data) -> Node:
        """Convert JSON/binding objects to RDFLib terms"""
        if isinstance(data, dict) and "type" in data and "value" in data:
            # SPARQL binding object - values may have been processed to RDFLib terms
            type_str = str(data["type"])  # Convert potential Literal to string
            value_str = str(data["value"])  # Convert potential Literal to string

            if type_str == "uri":
                return URIRef(value_str)
            elif type_str == "literal":
                datatype = data.get("datatype")
                lang = data.get("xml:lang")
                if datatype:
                    datatype = URIRef(str(datatype))
                if lang:
                    lang = str(lang)
                return Literal(value_str, datatype=datatype, lang=lang)
            elif type_str == "bnode":
                return BNode(value_str)
            else:
                raise ValueError(f"Unknown binding type: {type_str}")
        elif isinstance(data, (URIRef, Literal, BNode)):
            # Already RDFLib term
            return data
        elif hasattr(data, "__class__") and data.__class__.__name__ in [
            "JSONResult",
            "Result",
        ]:
            # Result should pass through unchanged
            return data
        elif isinstance(data, str):
            # Plain string → always convert to string literal
            return Literal(data, datatype=XSD.string)
        elif isinstance(data, int):
            return Literal(data, datatype=XSD.integer)
        elif isinstance(data, float):
            return Literal(data, datatype=XSD.double)
        elif isinstance(data, bool):
            return Literal(data, datatype=XSD.boolean)
        else:
            # Default: convert to string literal
            return Literal(str(data), datatype=XSD.string)

    @staticmethod
    def plain_to_rdflib(value: Any) -> Node:
        """Convert plain Python values to RDFLib terms for MCP interface"""
        if isinstance(value, str):
            # Plain string → always convert to string literal
            return Literal(value, datatype=XSD.string)
        elif isinstance(value, int):
            return Literal(value, datatype=XSD.integer)
        elif isinstance(value, float):
            return Literal(value, datatype=XSD.double)
        elif isinstance(value, bool):
            return Literal(value, datatype=XSD.boolean)
        else:
            return Literal(str(value), datatype=XSD.string)

    @staticmethod
    def to_string_literal(term: Node) -> Literal:
        """Convert Literal terms to string-compatible literals, following SPARQL semantics"""
        if isinstance(term, Literal):
            # Both xsd:string and rdf:langString are string-compatible in SPARQL
            if term.datatype == XSD.string:
                return term  # Already xsd:string, return as-is
            elif term.language is not None:
                return term  # rdf:langString (datatype=None, lang=xx), return as-is (compatible with string operations)
            elif term.datatype is None and term.language is None:
                # Plain literal without datatype or language - treat as string
                return term
            else:
                # Other literal datatypes need explicit conversion
                raise TypeError(
                    f"Cannot implicitly convert {term.datatype} to string. Use Str() operation for explicit casting."
                )
        else:
            # URIRef, BNode, etc. require explicit casting
            raise TypeError(
                f"Cannot implicitly convert {type(term).__name__} to string. Use Str() operation for explicit casting."
            )

    @staticmethod
    def rdflib_to_plain(term: Node) -> Any:
        """Convert RDFLib terms to plain Python values for MCP interface"""
        if isinstance(term, URIRef):
            return str(term)
        elif isinstance(term, Literal):
            # Convert based on datatype
            if term.datatype == XSD.integer:
                return int(term)
            elif term.datatype == XSD.double or term.datatype == XSD.float:
                return float(term)
            elif term.datatype == XSD.boolean:
                return term.toPython()
            else:
                return str(term)
        elif isinstance(term, BNode):
            return str(term)
        else:
            return str(term)
