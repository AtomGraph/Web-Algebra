from typing import Any, Optional, Sequence, Union
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.operation import Operation
from web_algebra.operations.linkeddatahub.fragments import fragment_id
from web_algebra.operations.linked_data.post import POST


class AddResultSetChart(POST):
    @classmethod
    def name(cls):
        return "ldh-AddResultSetChart"

    @classmethod
    def description(cls) -> str:
        return """Writes a chart of SPARQL SELECT query results to a LinkedDataHub document.
        The chart is a resource the document holds, not one of its content blocks: to show it in the content mode,
        place it with ldh-AddObjectBlock, the chart's URI as its value - so give the chart a fragment identifier.
        
        A chart shows values: the query's bindings themselves, as a table or a plot, the way a spreadsheet would.
        It is the fit for aggregates and measurements - totals, counts, sums per shop or per month. A resource in
        a chart is a bare cell, with no image, label or links of its own: to show resources themselves (things,
        people, places), use ldh-AddView, whose modes render each one as itself.
        
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
                    "description": "The URI of the document to write the chart to.",
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
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": "Name of the SPARQL variable used as series/value (without leading '?'), or an array of names for several series.",
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

    def execute_json(self, arguments: dict[str, str], variable_stack: list = None) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"AddResultSetChart operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, URIRef):
            raise TypeError(
                f"AddResultSetChart operation expects 'query' to be URIRef, got {type(query_data)}"
            )

        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title_literal = self.to_string_literal(title_data)

        chart_type_data = Operation.process_json(
            self.settings, arguments["chart_type"], self.context, variable_stack
        )
        if not isinstance(chart_type_data, URIRef):
            raise TypeError(
                f"AddResultSetChart operation expects 'chart_type' to be URIRef, got {type(chart_type_data)}"
            )

        category_var_name_data = Operation.process_json(
            self.settings, arguments["category_var_name"], self.context, variable_stack
        )
        category_var_name_literal = self.to_string_literal(category_var_name_data)

        series_var_name_data = Operation.process_json(
            self.settings, arguments["series_var_name"], self.context, variable_stack
        )
        # a name, or a sequence of names - one series each
        if isinstance(series_var_name_data, list):
            series_var_name_literal = [self.to_string_literal(name) for name in series_var_name_data]
        else:
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
            url_data,
            query_data,
            title_literal,
            chart_type_data,
            category_var_name_literal,
            series_var_name_literal,
            description_literal,
            fragment_literal,
        )

    def execute(
        self,
        url: URIRef,
        query: URIRef,
        title: Literal,
        chart_type: URIRef,
        category_var_name: Literal,
        series_var_name: Union[Literal, Sequence[Literal]],
        description: Optional[Literal] = None,
        fragment: Optional[Literal] = None,
    ) -> Any:
        """Pure function: create SPARQL result set chart with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddResultSetChart.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(query, URIRef):
            raise TypeError(
                f"AddResultSetChart.execute expects query to be URIRef, got {type(query)}"
            )
        if not Operation.is_string_compatible(title):
            raise TypeError(
                f"AddResultSetChart.execute expects title to be string Literal, got {type(title)}"
            )
        if not isinstance(chart_type, URIRef):
            raise TypeError(
                f"AddResultSetChart.execute expects chart_type to be URIRef, got {type(chart_type)}"
            )
        if (
            not Operation.is_string_literal(category_var_name)
        ):
            raise TypeError(
                f"AddResultSetChart.execute expects category_var_name to be string Literal, got {type(category_var_name)}"
            )
        series_var_names = series_var_name if isinstance(series_var_name, (list, tuple)) else [series_var_name]
        if not series_var_names or not all(Operation.is_string_literal(name) for name in series_var_names):
            raise TypeError(
                f"AddResultSetChart.execute expects series_var_name to be a string Literal or a non-empty sequence of them, got {series_var_name!r}"
            )
        if description is not None and (
            not Operation.is_string_compatible(description)
        ):
            raise TypeError(
                f"AddResultSetChart.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not Operation.is_string_literal(fragment)
        ):
            raise TypeError(
                f"AddResultSetChart.execute expects fragment to be string Literal, got {type(fragment)}"
            )

        url_str = str(url)
        query_str = str(query)
        title_str = Operation.jsonld_text(title)
        chart_type_str = str(chart_type)
        category_var_name_str = str(category_var_name)
        series_var_name_strs = [str(name) for name in series_var_names]
        description_str = Operation.jsonld_text(description) if description else None
        fragment_str = fragment_id(fragment)

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
            "ldh:seriesVarName": series_var_name_strs if len(series_var_name_strs) > 1 else series_var_name_strs[0],
        }

        # Add optional properties - matching shell script conditional logic
        if description_str:
            data["dct:description"] = description_str

        logging.info(f"Posting ResultSetChart with JSON-LD data: {data}")

        # Convert the JSON-LD content to a Graph and POST to the target URI
        graph = self.to_graph(data, base=url_str)
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
        names = arguments["series_var_name"]
        series_var_name = (
            [Literal(name, datatype=XSD.string) for name in names]
            if isinstance(names, list)
            else Literal(names, datatype=XSD.string)
        )

        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)

        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        # Call pure function
        result = self.execute(
            url,
            query,
            title,
            chart_type,
            category_var_name,
            series_var_name,
            description,
            fragment,
        )

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [
            types.TextContent(type="text", text=f"Result set chart added - status: {status_binding}")
        ]
