import logging
import pprint
from rdflib import Variable, URIRef, Literal, BNode
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.algebra import translateQuery, translateAlgebra, CompValue
from operation import Operation

class Substitute(Operation):
    """
    Replaces variable placeholders in a SPARQL query with actual values from a given set of bindings.
    """

    def __init__(self, context: dict = None, query: str = None, var: str = None, binding: dict = None):
        """
        Initialize the Substitute operation.
        :param context: Execution context.
        :param query: The SPARQL query string.
        :param var: The variable to substitute.
        :param binding: The value to replace the variable with.
        """
        super().__init__(context)

        if query is None or var is None or binding is None:
            raise ValueError("Substitute operation requires 'query', 'var', and 'binding' to be set.")

        self.query = query
        self.var = Variable(var)  # Convert to an RDFLib Variable
        self.binding = binding  # Might be another operation to resolve

    def execute(self) -> str:
        """
        Executes the Substitute operation by replacing variables in the SPARQL algebra.
        """
        logging.info(f"Resolving SPARQL query for substitution: {self.query}")

        # ✅ Resolve `query` dynamically
        resolved_query = self.resolve_arg(self.query)
        logging.info(f"SPARQL query before substitution:\n{resolved_query}")

        # ✅ Parse SPARQL Query
        query_obj = translateQuery(parseQuery(resolved_query))
        algebra = query_obj.algebra  # Extract the algebra

        logging.info(f"SPARQL Algebra before substitution:\n{algebra}")

        # ✅ Resolve the binding dynamically
        resolved_binding = self.resolve_arg(self.binding)
        logging.info(f"Resolved binding: {resolved_binding}")
        binding_dict = {Variable(self.var): (
            URIRef(resolved_binding["value"]) if resolved_binding["type"] == "uri" else
            BNode(resolved_binding["value"]) if resolved_binding["type"] == "bnode" else
            Literal(resolved_binding["value"])
        )}

        # ✅ Apply substitution only to the WHERE clause
        where_clause = algebra.p
        substituted_where_clause = self.substitute(where_clause, binding_dict)

        logging.info(f"where_clause: %s", pprint.pformat(where_clause))
        # ✅ Update algebra with the modified WHERE clause
        algebra["p"] = substituted_where_clause  # ✅ Modify in place
        substituted_algebra = algebra  # ✅ Explicitly assign it back

        logging.info(f"substituted_where_clause:\n{pprint.pformat(substituted_where_clause)}")
        logging.info(f"substituted_algebra.__dict__:\n{substituted_algebra.__dict__}")
        logging.info(f"substituted_algebra:\n{pprint.pformat(substituted_algebra)}")

        # ✅ Convert back to SPARQL Query
        substituted_query = translateAlgebra(substituted_algebra)

        logging.info(f"SPARQL query after substitution:\n{substituted_query}")

        # ✅ Ensure substituted query is not empty
        if not substituted_query.strip():
            raise ValueError("Substituted query is empty!")

        return substituted_query

    @staticmethod
    def substitute(algebra, binding: dict):
        """
        Recursively substitutes variables in the SPARQL algebra structure.
        :param algebra: The SPARQL algebra tree (CompValue)
        :param binding: Dictionary of variable bindings { ?var -> value }
        :return: Transformed algebra with substitutions applied
        """

        logging.info(f"Substituting in algebra: {algebra}")

        if algebra is None:
            logging.error("Received None as algebra input!")
            return None

        # ✅ Replace variables directly if found in the binding
        if isinstance(algebra, Variable):
            logging.info(f"Variable {algebra} found in binding: {binding.get(algebra, algebra)}")
            return binding.get(algebra, algebra)

        # ✅ Handle leaf nodes (URIRef, Literal) → No change needed
        if isinstance(algebra, (URIRef, Literal)):
            logging.info(f"Leaf node (URIRef/Literal): {algebra}")
            return algebra

        # ✅ BGP (Basic Graph Pattern) substitution
        if algebra.name == "BGP":
            logging.info(f"Processing BGP: {algebra.triples}")
            return CompValue("BGP", triples=[
                (Substitute.substitute(s, binding),
                 Substitute.substitute(p, binding),
                 Substitute.substitute(o, binding))
                for s, p, o in algebra.triples
            ])

        # ✅ Filter substitution
        if algebra.name == "Filter":
            logging.info(f"Processing Filter: {algebra.expr}")
            return CompValue("Filter",
                             expr=Substitute.substitute(algebra.expr, binding),
                             p=Substitute.substitute(algebra.p, binding))

        # ✅ Join substitution
        if algebra.name == "Join":
            logging.info(f"Processing Join: {algebra.p1} - {algebra.p2}")
            return CompValue("Join",
                             p1=Substitute.substitute(algebra.p1, binding),
                             p2=Substitute.substitute(algebra.p2, binding))

        # ✅ Left Join
        if algebra.name == "LeftJoin":
            logging.info(f"Processing LeftJoin: {algebra.p1} - {algebra.p2}")
            return CompValue("LeftJoin",
                             p1=Substitute.substitute(algebra.p1, binding),
                             p2=Substitute.substitute(algebra.p2, binding),
                             expr=Substitute.substitute(algebra.expr, binding))

        # ✅ Union
        if algebra.name == "Union":
            logging.info(f"Processing Union: {algebra.p1} - {algebra.p2}")
            return CompValue("Union",
                             p1=Substitute.substitute(algebra.p1, binding),
                             p2=Substitute.substitute(algebra.p2, binding))

        # ✅ Graph substitution
        if algebra.name == "Graph":
            logging.info(f"Processing Graph: {algebra.term}")
            return CompValue("Graph",
                             term=Substitute.substitute(algebra.term, binding),
                             p=Substitute.substitute(algebra.p, binding))

        # ✅ Extend (LET binding)
        if algebra.name == "Extend":
            logging.info(f"Processing Extend: {algebra.var}")
            return CompValue("Extend",
                             p=Substitute.substitute(algebra.p, binding),
                             expr=Substitute.substitute(algebra.expr, binding),
                             var=algebra.var)  # Variable name itself is not substituted

        # ✅ Minus
        if algebra.name == "Minus":
            logging.info(f"Processing Minus: {algebra.p1} - {algebra.p2}")
            return CompValue("Minus",
                             p1=Substitute.substitute(algebra.p1, binding),
                             p2=Substitute.substitute(algebra.p2, binding))

        # ✅ OrderBy
        if algebra.name == "OrderBy":
            logging.info(f"Processing OrderBy: {algebra.expr}")
            return CompValue("OrderBy",
                             p=Substitute.substitute(algebra.p, binding),
                             expr=[Substitute.substitute(e, binding) for e in algebra.expr])

        # ✅ Project (SELECT variables)
        if algebra.name == "Project":
            logging.info(f"Processing Project: {algebra.PV}")
            return CompValue("Project",
                             p=Substitute.substitute(algebra.p, binding),
                             PV=[v for v in algebra.PV if isinstance(v, Variable)])  # Ensure only variables remain

        # ✅ Values clause substitution
        if algebra.name == "Values":
            logging.info(f"Processing Values: {algebra.res}")
            substituted_rows = [
                {k: Substitute.substitute(v, binding) for k, v in row.items()}
                for row in algebra.res
            ]
            return CompValue("Values", res=substituted_rows)

        # ✅ Generic case: Apply substitution to all attributes recursively
        try:
            logging.info(f"Processing generic case: {algebra.name}")
            result = CompValue(algebra.name, **{
                k: Substitute.substitute(v, binding) for k, v in algebra.items()
            })
            logging.info(f"Substitution result: {result}")
            return result
        except Exception as e:
            logging.error(f"Error substituting {algebra}: {e}")
            return None
