import argparse
import logging
import os
import sys
import json
from types import ModuleType
from typing import List, Type, Optional
import pkgutil
import importlib
import inspect
from openai import OpenAI
from pydantic_settings import BaseSettings
from operation import Operation
import operations
from operations.get import GET
from operations.put import PUT
from operations.post import POST
# from operations.delete import DELETE

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,  # ✅ Show INFO, WARNING, ERROR, and CRITICAL messages
    format="%(asctime)s - %(levelname)s - %(message)s",  # ✅ Add timestamps for clarity
    handlers=[logging.StreamHandler()]  # ✅ Ensure output goes to console
)

class LinkedDataHubSettings(BaseSettings):
    cert_pem_path: str
    cert_password: str

def list_operation_subclasses(
    pkg: ModuleType,
    base_class: Type[Operation]
) -> List[Type[Operation]]:
    subclasses = []

    for loader, module_name, is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        module = importlib.import_module(module_name)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Filter: class defined in the module AND is a subclass of Operation (but not Operation itself)
            if (
                obj.__module__ == module.__name__ and
                issubclass(obj, base_class) and
                obj is not base_class
            ):
                subclasses.append(obj)

    return subclasses

def register(classes: List[Type[Operation]]):
    for cls in classes:
        Operation.register(cls)

def main(settings: BaseSettings, json_data: Optional[str]):
    register(list_operation_subclasses(operations, Operation))

    if json_data:
        logging.info("Executing from JSON input %s", json_data)
        # Load JSON input from file
        with open(json_data) as json_file:
            json_input = json.load(json_file)

        # Execute the JSON input
        print(Operation.execute_json(settings, json_input))
    else:
        # Load API key
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            sys.exit("Error: Environment variable OPENAI_API_KEY is not set.")

        client = OpenAI(api_key=api_key)
        model = "gpt-4o-mini"

        # Load prompts
        with open("prompts/system.md") as system_prompt_file, open("prompts/user.template.txt") as user_prompt_template_file:
            system_prompt = system_prompt_file.read()
            messages = [ {"role": "system", "content": system_prompt} ]

            user_prompt_template = user_prompt_template_file.read()

            while True:
                instruction = input("Instruction: ")

                user_prompt = user_prompt_template.format(instruction=instruction)
                messages.append(
                    {"role": "user", "content": user_prompt},
                )

                chat_completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={ "type": "json_object" }
                )

                reply_json = json.loads(chat_completion.choices[0].message.content)
                assert isinstance(reply_json, dict)
                logging.info("Generated response: %s", reply_json)

                # Execute the generated operation
                print(Operation.execute_json(settings, reply_json))


if __name__ == "__main__":
    # Parse script arguments
    parser = argparse.ArgumentParser(description="Run the AI-powered DSL interpreter.")
    parser.add_argument(
        "--from-json",
        type=str,
        help="JSON input file to execute",
    )
    parser.add_argument(
        "--cert_pem_path",
        type=str,
        help="Path to the client certificate PEM file",
    )
    parser.add_argument(
        "--cert_password",
        type=str,
        help="Password for the client certificate",
    )
    args = parser.parse_args()

    if args.cert_pem_path and args.cert_password:
        settings = LinkedDataHubSettings(cert_pem_path = args.cert_pem_path, cert_password = args.cert_password)
    else:
        settings = BaseSettings()
    
    main(settings, args.from_json)
