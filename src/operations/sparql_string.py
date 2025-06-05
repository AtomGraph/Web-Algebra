import logging
from typing import Any
from openai import OpenAI
from operation import Operation

class SPARQLString(Operation):
    """
    Converts a natural language question into a SPARQL query using OpenAI API.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = OpenAI(api_key=getattr(self.settings, 'openai_api_key', None))
        self.model = getattr(self.settings, 'openai_model', None)

    @property
    def description(self) -> str:
        return """
        Converts a natural language question into a SPARQL query string.
        This operation uses OpenAI's API to generate a structured SPARQL query based on the provided question.
        The generated query will include necessary PREFIX declarations and will be formatted as a valid SPARQL query string.
        """
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Generates a SPARQL query string from a natural language question.
        :param arguments: A dictionary containing:
            - `question`: The natural language question to convert into a SPARQL query.
        :return: A valid SPARQL query string.
        """
        question: str = Operation.execute_json(self.settings, arguments["question"], self.context)
        logging.info(f"Resolving question: %s", question)

        # ✅ Call OpenAI API with JSON mode to generate a structured SPARQL query
        chat_completion = self.client.chat.completions.create(
            model=self.model,  # ✅ Use dynamic model
            messages=[
                {"role": "system", "content": "You are an expert in RDF and SPARQL. Generate a valid SPARQL query based on the given natural language question."},
                {"role": "user", "content": f"Convert this into a SPARQL query:\nQuestion: {question}\nRemember to include the necessary PREFIX declarations. Provide only the query string, no explanations or comments or markdown formatting."},
            ],
        )

        result = chat_completion.choices[0].message.content
        logging.info("Generated SPARQL query: %s, result")
        return result
