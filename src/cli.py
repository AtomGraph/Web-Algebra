import os
import logging
from openai import OpenAI

# Load API key
if os.getenv("OPENAI_API_KEY"):
    api_key = os.getenv("OPENAI_API_KEY")
    logging.info("Loaded API key from environment variable")
else:
    try:
        with open('../api-key.txt') as apiKeyFile:
            api_key = apiKeyFile.read().rstrip()
            logging.info("Loaded API key from file")
    except Exception as e:
        logging.error("Failed to load API key: %s", e)
        raise

client = OpenAI(api_key=api_key)
model = "gpt-4o-mini"

# Load prompts
with open("prompts/system.md") as system_prompt_file, open("prompts/user.template.txt") as user_prompt_template_file:
    system_prompt = system_prompt_file.read()
    messages = [ {"role": "system", "content": system_prompt} ]

    user_prompt_template = user_prompt_template_file.read()

    while True:
        try:
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
            
            reply = chat_completion.choices[0].message.content
            print(reply)
            logging.info("Generated response: %s", reply)
        except Exception as e:
            logging.error("Error during chat completion: %s", e)
