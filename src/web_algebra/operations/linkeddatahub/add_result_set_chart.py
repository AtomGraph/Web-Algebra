from typing import Any
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST


class AddResultSetChart(POST):
    @classmethod
    def name(cls):
        return "ldh-AddResultSetChart"

    @classmethod
    def description(cls) -> str:
        return """Appends a chart for SPARQL SELECT query results to a LinkedDataHub document.
        
        This tool creates a ResultSetChart that visualizes data from SPARQL SELECT query resources.
        The chart references an existing sp:Select resource (not a query string) and can display 
        results using different chart types (bar, line, pie, etc.) with variable mappings.
        
        This tool:
        - Creates an ldh:ResultSetChart resource linked to an existing sp:Select query resource
        - Configures chart type and variable mappings for visualization
        - Posts the new chart resource to the target document
        - Supports optional title, description, and fragment identifier
        
        Possible chart types include:
        - https://w3id.org/atomgraph/client#Table: Table visualization of results
        - https://w3id.org/atomgraph/client#BarChart: Bar chart visualization
        - https://w3id.org/atomgraph/client#LineChart: Line chart visualization
        - https://w3id.org/atomgraph/client#ScatterChart: Scatter chart visualization
        - https://w3id.org/atomgraph/client#Timeline: Timeline visualization

        Note: The query parameter must be a URI of an existing sp:Select resource, not a SPARQL query string."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URI of the document to append the chart to.",
                },
                "query": {
                    "type": "string",
                    "description": "URI of an existing sp:Select query resource to visualize (not a SPARQL query string).",
                },
                "title": {"type": "string", "description": "Title of the chart."},
                "chart_type": {
                    "type": "string",
                    "description": "URI of the chart type (e.g., https://w3id.org/atomgraph/client#BarChart).",
                    "enum": [
                        "https://w3id.org/atomgraph/client#Table",
                        "https://w3id.org/atomgraph/client#BarChart",
                        "https://w3id.org/atomgraph/client#LineChart",
                        "https://w3id.org/atomgraph/client#ScatterChart",
                        "https://w3id.org/atomgraph/client#Timeline",
                    ],
                },
                "category_var_name": {
                    "type": "string",
                    "description": "Name of the SPARQL variable used as category (without leading '?').",
                },
                "series_var_name": {
                    "type": "string",
                    "description": "Name of the SPARQL variable used as series/value (without leading '?').",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of the chart.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the chart URI (e.g., 'my-chart' creates #my-chart).",
                },
            },
            "required": [
                "url",
                "query",
                "title",
                "chart_type",
                "category_var_name",
                "series_var_name",
            ],
        }

    def execute_json(self, arguments: dict[str, str], variable_stack: list = []) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(f"AddResultSetChart operation expects 'url' to be URIRef, got {type(url_data)}")

        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, URIRef):
            raise TypeError(f"AddResultSetChart operation expects 'query' to be URIRef, got {type(query_data)}")

        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title_literal = self.to_string_literal(title_data)

        chart_type_data = Operation.process_json(
            self.settings, arguments["chart_type"], self.context, variable_stack
        )
        if not isinstance(chart_type_data, URIRef):
            raise TypeError(f"AddResultSetChart operation expects 'chart_type' to be URIRef, got {type(chart_type_data)}")

        category_var_name_data = Operation.process_json(
            self.settings, arguments["category_var_name"], self.context, variable_stack
        )
        category_var_name_literal = self.to_string_literal(category_var_name_data)

        series_var_name_data = Operation.process_json(
            self.settings, arguments["series_var_name"], self.context, variable_stack
        )
        series_var_name_literal = self.to_string_literal(series_var_name_data)

        # Process optional arguments
        description_literal = None
        if "description" in arguments:
            description_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            description_literal = self.to_string_literal(description_data)

        fragment_literal = None
        if "fragment" in arguments:
            fragment_data = Operation.process_json(
                self.settings, arguments["fragment"], self.context, variable_stack
            )
            fragment_literal = self.to_string_literal(fragment_data)
            
        return self.execute(
            url_data, query_data, title_literal, chart_type_data,
            category_var_name_literal, series_var_name_literal,
            description_literal, fragment_literal
        )

    def execute(
        self,
        url: URIRef,
        query: URIRef,
        title: Literal,
        chart_type: URIRef,
        category_var_name: Literal,
        series_var_name: Literal,
        description: Literal = None,
        fragment: Literal = None,
    ) -> Any:
        """Pure function: create SPARQL result set chart with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"AddResultSetChart.execute expects url to be URIRef, got {type(url)}")
        if not isinstance(query, URIRef):
            raise TypeError(f"AddResultSetChart.execute expects query to be URIRef, got {type(query)}")
        if not isinstance(title, Literal) or title.datatype != XSD.string:
            raise TypeError(f"AddResultSetChart.execute expects title to be string Literal, got {type(title)}")
        if not isinstance(chart_type, URIRef):
            raise TypeError(f"AddResultSetChart.execute expects chart_type to be URIRef, got {type(chart_type)}")
        if not isinstance(category_var_name, Literal) or category_var_name.datatype != XSD.string:
            raise TypeError(f"AddResultSetChart.execute expects category_var_name to be string Literal, got {type(category_var_name)}")
        if not isinstance(series_var_name, Literal) or series_var_name.datatype != XSD.string:
            raise TypeError(f"AddResultSetChart.execute expects series_var_name to be string Literal, got {type(series_var_name)}")
        if description is not None and (not isinstance(description, Literal) or description.datatype != XSD.string):
            raise TypeError(f"AddResultSetChart.execute expects description to be string Literal, got {type(description)}")
        if fragment is not None and (not isinstance(fragment, Literal) or fragment.datatype != XSD.string):
            raise TypeError(f"AddResultSetChart.execute expects fragment to be string Literal, got {type(fragment)}")

        url_str = str(url)
        query_str = str(query)
        title_str = str(title)
        chart_type_str = str(chart_type)
        category_var_name_str = str(category_var_name)
        series_var_name_str = str(series_var_name)
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None

        logging.info(
            "Creating ResultSetChart for document <%s> with sp:Select resource <%s>",
            url_str,
            query_str,
        )

        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment_str:
            subject_id = f"#{fragment_str}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"

        # Build JSON-LD structure for the chart - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "spin": "http://spinrdf.org/spin#",
            },
            "@id": subject_id,
            "@type": "ldh:ResultSetChart",
            "dct:title": title_str,
            "spin:query": {"@id": query_str},
            "ldh:chartType": {"@id": chart_type_str},
            "ldh:categoryVarName": category_var_name_str,
            "ldh:seriesVarName": series_var_name_str,
        }

        # Add optional properties - matching shell script conditional logic
        if description_str:
            data["dct:description"] = description_str

        logging.info(f"Posting ResultSetChart with JSON-LD data: {data}")

        # POST the JSON-LD content to the target URI
        # Convert JSON-LD dict to Graph
        import json
        from rdflib import Graph
        graph = Graph()
        graph.parse(data=json.dumps(data), format="json-ld")
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types
        
        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        query = URIRef(arguments["query"])
        title = Literal(arguments["title"], datatype=XSD.string)
        chart_type = URIRef(arguments["chart_type"])
        category_var_name = Literal(arguments["category_var_name"], datatype=XSD.string)
        series_var_name = Literal(arguments["series_var_name"], datatype=XSD.string)
        
        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)
            
        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        # Call pure function
        result = self.execute(url, query, title, chart_type, category_var_name, 
                            series_var_name, description, fragment)

        # Return status for MCP response
        return [types.TextContent(type="text", text=f"Result set chart added successfully")]
