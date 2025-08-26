import logging
from typing import Any
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from openai import OpenAI
from web_algebra.operation import Operation


class SPARQLString(Operation):
    """
    Converts a natural language question into a SPARQL query using OpenAI API.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = OpenAI(api_key=getattr(self.settings, "openai_api_key", None))
        self.model = getattr(self.settings, "openai_model", None)

    @classmethod
    def description(cls) -> str:
        return """
        Converts a natural language question into a SPARQL query string.
        This operation uses OpenAI's API to generate a structured SPARQL query based on the provided question.
        The generated query will include necessary PREFIX declarations and will be formatted as a valid SPARQL query string.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The natural language question to convert into a SPARQL query.",
                }
            },
            "required": ["question"],
        }

    def execute(self, question: Literal) -> Literal:
        """Pure function: generate SPARQL query from question with RDFLib terms"""
        if not isinstance(question, Literal):
            raise TypeError(
                f"SPARQLString.execute expects question to be Literal, got {type(question)}"
            )

        question_str = str(question)
        logging.info("Generating SPARQL query for question: %s", question_str)

        # Call OpenAI API to generate SPARQL query
        chat_completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in RDF and SPARQL. Generate a valid SPARQL query based on the given natural language question.",
                },
                {
                    "role": "user",
                    "content": f"Convert this into a SPARQL query:\nQuestion: {question_str}\nRemember to include the necessary PREFIX declarations. Provide only the query string, no explanations or comments or markdown formatting.",
                },
            ],
        )

        result = chat_completion.choices[0].message.content
        logging.info("Generated SPARQL query: %s", result)
        return Literal(result, datatype=XSD.string)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
        """JSON execution: process arguments and delegate to execute()"""
        question_data = Operation.process_json(
            self.settings, arguments["question"], self.context, variable_stack
        )
        # Allow implicit string conversion
        question_literal = Operation.to_string_literal(question_data)

        return self.execute(question_literal)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        question = Literal(arguments["question"], datatype=XSD.string)

        result = self.execute(question)
        return [types.TextContent(type="text", text=str(result))]
