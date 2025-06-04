from abc import ABC, abstractmethod
import logging
from typing import Type, Dict, Optional, Any, List, ClassVar
from mcp import Tool
from pydantic_settings import BaseSettings

class Operation(ABC, Tool):
    """
    Abstract base class for all operations. Ensures all operations implement the execute method
    and provides metadata for introspection.
    """

    registry: ClassVar[Dict[str, Type["Operation"]]] = {}
    settings: BaseSettings
    
    @property
    def name(self) -> str:
        """
        The name of the operation, used for introspection and registration.
        :return: The class name of the operation.
        """
        return self.__class__.__name__
    
    @property
    @abstractmethod
    def description(self):
        """Subclasses must implement this property."""
        pass

    @property
    @abstractmethod
    def inputSchema(self):
        """
        Returns the JSON schema of the operation's input arguments.
        """
    pass

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> Any:
        """
        Execute the operation. Subclasses must implement this method.
        :return: The result of the operation execution.
        """
        pass

    @classmethod
    def register(cls, operation_cls: Type["Operation"]) -> None:
        """
        Register an operation class with its class name as the key.
        :param operation_cls: The Operation subclass.
        """
        if not issubclass(operation_cls, cls):
            raise ValueError(f"Cannot register {operation_cls}: Must be a subclass of Operation.")

        # ✅ Use the class name as the registry key
        operation_name = operation_cls.__name__
        cls.registry[operation_name] = operation_cls

        logging.info(f"Registered operation: {operation_name}")

    @classmethod
    def list_operations(self) -> List["Operation"]:
        """
        Returns a list of all registered operations.
        :return: A list of Operation subclasses.
        """
        return list(self.registry.values())
    
    @classmethod
    def get(cls, name: str) -> Optional[Type["Operation"]]:
        """
        Retrieve an operation class by its name.
        :param name: The name of the operation.
        :return: The Operation subclass or None if not found.
        """
        return cls.registry.get(name)

    @classmethod
    def execute_json(cls, settings: BaseSettings, json_data: dict) -> Any:
        """
        Resolves and executes an operation from JSON.
        :param operation_json: A dictionary representing the operation JSON.
        :return: The result of the operation execution.
        """
        logging.info(f"Processing JSON operation: {json_data}")

        if not isinstance(json_data, dict): # or len(json_data) != 1
            raise ValueError("Invalid operation format. Expected a dictionary") # Expected a single key dictionary.

        op_name, op_args = next(iter(json_data.items()))

        if not isinstance(op_args, dict):
            raise ValueError(f"Invalid arguments for operation '{op_name}'. Expected a dictionary.")

        # Resolve the correct Operation class via registry
        operation_cls = cls.get(op_name)
        if not operation_cls:
            raise ValueError(f"Unknown operation: {op_name}")

        operation = operation_cls(settings=settings)
        logging.info("'%s' operation initialized.", op_name)
        
        # Resolve each argument in op_args
        resolved_args = {k: operation.resolve_arg(v) for k, v in op_args.items()}

        # execute the operation with resolved arguments
        return operation.execute(resolved_args)

    def resolve_arg(self, arg: Any) -> Any:
        """
        Resolves an argument that could be:
        - A raw JSON-LD blob → returned as-is
        - An RDF term (dict with "type") → returned as-is
        - A function call (dict with an operation name) → executed and returned

        :param arg: The argument to resolve.
        :return: The resolved value.
        """

        # ✅ If arg is a dictionary, check if it's an RDF term or a function call
        if isinstance(arg, dict):
            if "@context" in arg:
                # ✅ Treat as inline JSON-LD blob, return as-is
                return arg
            
            if "type" in arg and "value" in arg:
                # ✅ Recognized as an RDF term → return as-is
                return arg

            # ✅ Otherwise, assume it's a function call and execute it
            return self.execute_json(self.settings, arg)

        # ✅ If arg is a raw value (string, number, etc.), return as-is
        return arg
