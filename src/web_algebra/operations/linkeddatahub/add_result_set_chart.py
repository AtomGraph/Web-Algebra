from typing import Any
import logging
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
                    "description": "The URI of the document to append the chart to."
                },
                "query": {
                    "type": "string", 
                    "description": "URI of an existing sp:Select query resource to visualize (not a SPARQL query string)."
                },
                "title": {
                    "type": "string", 
                    "description": "Title of the chart."
                },
                "chart_type": {
                    "type": "string", 
                    "description": "URI of the chart type (e.g., https://w3id.org/atomgraph/client#BarChart).",
                    "enum": [
                        "https://w3id.org/atomgraph/client#Table",
                        "https://w3id.org/atomgraph/client#BarChart",
                        "https://w3id.org/atomgraph/client#LineChart",
                        "https://w3id.org/atomgraph/client#ScatterChart",
                        "https://w3id.org/atomgraph/client#Timeline"
                    ]
                },
                "category_var_name": {
                    "type": "string", 
                    "description": "Name of the SPARQL variable used as category (without leading '?')."
                },
                "series_var_name": {
                    "type": "string", 
                    "description": "Name of the SPARQL variable used as series/value (without leading '?')."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the chart."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the chart URI (e.g., 'my-chart' creates #my-chart)."
                }
            },
            "required": ["url", "query", "title", "chart_type", "category_var_name", "series_var_name"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a SPARQL result set chart resource, matching the reference shell script
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to post to
            - `query`: URI of an existing sp:Select query resource (not a query string)
            - `title`: Title of the chart
            - `chart_type`: URI of the chart type
            - `category_var_name`: Variable name for category axis
            - `series_var_name`: Variable name for series/value axis
            - `description`: Optional description
            - `fragment`: Optional fragment identifier
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("AddResultSetChart operation expects 'url' to be a string.")
        
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        if not isinstance(query, str):
            raise ValueError("AddResultSetChart operation expects 'query' to be a URI string referencing an sp:Select resource.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("AddResultSetChart operation expects 'title' to be a string.")
        
        chart_type: str = Operation.execute_json(self.settings, arguments["chart_type"], self.context)
        if not isinstance(chart_type, str):
            raise ValueError("AddResultSetChart operation expects 'chart_type' to be a string.")
        
        category_var_name: str = Operation.execute_json(self.settings, arguments["category_var_name"], self.context)
        if not isinstance(category_var_name, str):
            raise ValueError("AddResultSetChart operation expects 'category_var_name' to be a string.")
        
        series_var_name: str = Operation.execute_json(self.settings, arguments["series_var_name"], self.context)
        if not isinstance(series_var_name, str):
            raise ValueError("AddResultSetChart operation expects 'series_var_name' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("AddResultSetChart operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("AddResultSetChart operation expects 'fragment' to be a string.")
        
        logging.info(f"Creating ResultSetChart for document <%s> with sp:Select resource <%s>", url, query)
        
        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment:
            subject_id = f"#{fragment}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"
        
        # Build JSON-LD structure for the chart - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "spin": "http://spinrdf.org/spin#"
            },
            "@id": subject_id,
            "@type": "ldh:ResultSetChart",
            "dct:title": title,
            "spin:query": {
                "@id": query
            },
            "ldh:chartType": {
                "@id": chart_type
            },
            "ldh:categoryVarName": category_var_name,
            "ldh:seriesVarName": series_var_name
        }
        
        # Add optional properties - matching shell script conditional logic
        if description:
            data["dct:description"] = description
        
        logging.info(f"Posting ResultSetChart with JSON-LD data: {data}")
        
        # POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
