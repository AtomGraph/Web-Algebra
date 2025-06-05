from abc import ABC, abstractmethod
import logging
from typing import Type, Dict, Optional, Any, List, ClassVar
from mcp import Tool
from pydantic_settings import BaseSettings


class Operation(ABC, Tool):
    """
    Abstract base class for all operations. Ensures all operations implement the execute method
    and provides metadata for introspection and registration.
    """

    registry: ClassVar[Dict[str, Type["Operation"]]] = {}
    settings: BaseSettings
    context: dict
  
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    @abstractmethod
    def description(self):
        pass

    @property
    @abstractmethod
    def inputSchema(self):
        pass

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> Any:
        pass

    @classmethod
    def register(cls, operation_cls: Type["Operation"]) -> None:
        if not issubclass(operation_cls, cls):
            raise ValueError(f"Cannot register {operation_cls}: Must be a subclass of Operation.")
        cls.registry[operation_cls.__name__] = operation_cls
        logging.info(f"Registered operation: {operation_cls.__name__}")

    @classmethod
    def list_operations(cls) -> List["Operation"]:
        return list(cls.registry.values())

    @classmethod
    def get(cls, name: str) -> Optional[Type["Operation"]]:
        return cls.registry.get(name)

    @classmethod
    def execute_json(cls, settings: BaseSettings, json_data: Any, context: dict = {}) -> Any:
        if isinstance(json_data, dict):
            if "@op" in json_data:
                op_name = json_data["@op"]
                op_args = json_data.get("args", {})

                operation_cls = cls.get(op_name)
                if not operation_cls:
                    raise ValueError(f"Unknown operation: {op_name}")

                operation = operation_cls(settings=settings, context=context)
                return operation.execute(op_args)  # Let each op resolve its own args

            # 🔁 Recurse into each value — allows nested @op inside JSON-LD
            return {
                k: cls.execute_json(settings, v, context)
                for k, v in json_data.items()
            }

        elif isinstance(json_data, list):
            return [cls.execute_json(settings, item, context) for item in json_data]

        else:
            return json_data
