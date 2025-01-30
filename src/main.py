import argparse
import logging
import os
import sys
import json
from openai import OpenAI
from operation import Operation
from operations.resolve_uri import ResolveURI
from operations.sparql_string import SPARQLString
from operations.get import GET
from operations.put import PUT
from operations.for_each import ForEach
from operations.value_of import ValueOf
from operations.select import SELECT
from operations.encode_for_uri import EncodeForURI
from operations.format_string import FormatString

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,  # ✅ Show INFO, WARNING, ERROR, and CRITICAL messages
    format="%(asctime)s - %(levelname)s - %(message)s",  # ✅ Add timestamps for clarity
    handlers=[logging.StreamHandler()]  # ✅ Ensure output goes to console
)

def main():
    # Parse script arguments
    parser = argparse.ArgumentParser(description="Run the AI-powered orchestrator.")
    parser.add_argument(
        "--cert_pem_path",
        type=str,
        required=True,
        help="Path to the client certificate PEM file",
    )
    parser.add_argument(
        "--cert_password",
        type=str,
        required=True,
        help="Password for the client certificate",
    )
    args = parser.parse_args()

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        sys.exit("Error: Environment variable OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    model = "gpt-4o-mini"

    GET.cert_pem_path = args.cert_pem_path
    GET.cert_password = args.cert_password
    PUT.cert_pem_path = args.cert_pem_path
    PUT.cert_password = args.cert_password

    Operation.register(ResolveURI)
    Operation.register(SPARQLString)
    Operation.register(SELECT)
    Operation.register(GET)
    Operation.register(PUT)
    Operation.register(ForEach)
    Operation.register(ValueOf)
    Operation.register(EncodeForURI)
    Operation.register(FormatString)

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
            print(Operation.execute_json(reply_json))


if __name__ == "__main__":
    main()
