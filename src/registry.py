from operation import Operation

class OperationRegistry:
    def __init__(self):
        self._operations = {}

    def register(self, name: str, operation: Operation):
        """
        Register an operation with a specific name.
        :param name: The name of the operation.
        :param operation: The operation instance.
        """
        self._operations[name] = operation

    def get(self, name: str) -> Operation:
        """
        Retrieve an operation by its name.
        :param name: The name of the operation.
        :return: The operation instance.
        """
        operation = self._operations.get(name)
        if not operation:
            raise ValueError(f"Operation '{name}' not found in the registry.")
        return operation

    def invoke(self, name: str, args: dict):
        """
        Invoke an operation by its name with arguments.
        :param name: The name of the operation to invoke.
        :param args: A dictionary of arguments for the operation's execute method.
        :return: The result of the operation's execution.
        """
        operation = self.get(name)
        return operation.execute(**args)

    def list_operations(self) -> list:
        """
        Return a list of all registered operation instances.
        :return: A list of operation instances.
        """
        return list(self._operations.values())
