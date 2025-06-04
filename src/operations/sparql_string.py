import os
import logging
from typing import ClassVar
from openai import OpenAI
from operation import Operation

class SPARQLString(Operation):
    """
    Converts a natural language question into a SPARQL query using OpenAI API.
    """

    model: str = "gpt-4o-mini"
    api_key: str = os.getenv("OPENAI_API_KEY")
    question: str  # Can be a direct string or a nested operation producing the question
    endpoint: str  # The SPARQL endpoint

    def execute(self) -> str:
        """
        Generates a SPARQL query string from a natural language question.
        :return: A valid SPARQL query string.
        """
        logging.info(f"Resolving question: {self.question}")

        # ✅ Resolve `question` dynamically 
        resolved_question = self.resolve_arg(self.question)
        logging.info(f"Generating SPARQL query for question: {resolved_question}")

        # ✅ Call OpenAI API with JSON mode to generate a structured SPARQL query
        chat_completion = self.client.chat.completions.create(
            model=self.model,  # ✅ Use dynamic model
            messages=[
                {"role": "system", "content": "You are an expert in RDF and SPARQL. Generate a valid SPARQL query based on the given natural language question."},
                {"role": "user", "content": f"Convert this into a SPARQL query:\nQuestion: {resolved_question}\nRemember to include the necessary PREFIX declarations. Provide only the query string, no explanations or comments or markdown formatting."},
            ],
        )

        result = chat_completion.choices[0].message.content
        logging.info(f"Generated SPARQL query: {result}")
        return result
