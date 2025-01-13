from abc import ABC, abstractmethod
import inspect
from typing import Optional, get_type_hints

class Operation(ABC):
    """
    Abstract base class for all operations. Ensures all operations implement the execute method
    and provide metadata for introspection.
    """

    @abstractmethod
    def execute(self, **kwargs):
        """
        Execute the operation. Subclasses must implement this method.
        """
        pass

    def metadata(self) -> dict:
        """
        Dynamically generate metadata for the operation by inspecting its execute method.
        :return: A dictionary containing the operation's name, description, and input schema.
        """
        # Introspect the `execute` method
        sig = inspect.signature(self.execute)
        docstring = inspect.getdoc(self.execute) or "No description provided."

        # Extract argument details
        args_schema = {}
        required_args = []
        type_hints = get_type_hints(self.execute)

        for name, param in sig.parameters.items():
            if name == "self":  # Skip `self`
                continue

            # Determine type and whether it's optional
            param_type = type_hints.get(name, str)  # Default to string if no type hint
            is_optional = param.default is not inspect.Parameter.empty

            # Build schema for the argument
            args_schema[name] = {
                "type": param_type.__name__ if hasattr(param_type, "__name__") else str(param_type),
                "description": f"The {name} argument.",
            }

            if not is_optional:
                required_args.append(name)

        # Construct the input schema
        input_schema = {
            "type": "object",
            "properties": args_schema,
            "required": required_args,
        }

        return {
            "name": self.__class__.__name__,
            "description": docstring,
            "inputSchema": input_schema,
        }
