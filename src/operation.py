from abc import ABC, abstractmethod
import logging
from typing import Type, Dict, Optional, Any

class Operation(ABC):
    """
    Abstract base class for all operations. Ensures all operations implement the execute method
    and provides metadata for introspection.
    """

    _registry: Dict[str, Type["Operation"]] = {}

    def __init__(self, context: dict):
        """
        Initialize the operation.
        :param context: Execution context.
        """
        self.context = context or {}
    
    @abstractmethod
    def execute(self) -> Any:
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
        cls._registry[operation_name] = operation_cls

        logging.info(f"Registered operation: {operation_name}")

    @classmethod
    def get(cls, name: str) -> Optional[Type["Operation"]]:
        """
        Retrieve an operation class by its name.
        :param name: The name of the operation.
        :return: The Operation subclass or None if not found.
        """
        return cls._registry.get(name)

    @classmethod
    def from_json(cls, json_data: dict, context: dict = None) -> "Operation":
        """
        Instantiates an Operation subclass from JSON.

        :param json_data: A dictionary representing the operation JSON.
        :param context: Execution context.
        :return: An Operation instance.
        """
        logging.info(f"Processing JSON operation: {json_data}")

        if not isinstance(json_data, dict) or len(json_data) != 1:
            raise ValueError("Invalid operation format. Expected a single key dictionary.")

        op_name, op_args = next(iter(json_data.items()))

        if not isinstance(op_args, dict):
            raise ValueError(f"Invalid arguments for operation '{op_name}'. Expected a dictionary.")

        # Resolve the correct Operation class via registry
        operation_cls = cls.get(op_name)
        if not operation_cls:
            raise ValueError(f"Unknown operation: {op_name}")

        # Instantiate the operation with the execution context
        return operation_cls(context, **op_args)

    @classmethod
    def execute_json(cls, operation_json: dict, context: dict = None) -> Any:
        """
        Resolves and executes an operation from JSON.
        :param operation_json: A dictionary representing the operation JSON.
        :param context: Execution context.
        :return: The result of the operation execution.
        """
        operation_instance = cls.from_json(operation_json, context or {})
        return operation_instance.execute()

    def resolve_arg(self, arg: Any) -> Any:
        """
        Resolves an argument that could either be a raw value or a nested operation.
        If it's a nested operation (dict), it is executed first.

        :param arg: The argument to resolve.
        :return: The resolved value.
        """
        return self.execute_json(arg, self.context) if isinstance(arg, dict) else arg
