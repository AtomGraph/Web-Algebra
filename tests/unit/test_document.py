"""Spec: formal-semantics.md §2 (Document Model) and §3 (Evaluation Semantics).

Covers form discrimination and scalar coercion (§2.2), the URI reference
form, sequence/variable scoping (§3.2, §3.4), and flat sequences (§3.1,
§3.8 SEQ): a sequence's value is the concatenation of its element values — a
sequence-valued element contributes its items, Unit (and so `Variable`)
contributes none, and a Result is one item, never dissolved into rows.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation


class TestURIReferenceForm:
    def test_id_string_evaluates_to_uri(self, settings):
        # §2.2 rule 2: an object whose only member is `@id` evaluates to a URI
        result = Operation.process_json(settings, {"@id": "http://example.org/x"})
        assert result == URIRef("http://example.org/x")

    def test_id_with_nested_operation(self, settings):
        # §2.2: the inner form may be any form that evaluates to a Term
        result = Operation.process_json(
            settings,
            {"@id": {"@op": "Concat", "args": {"inputs": ["http://ex/", "x"]}}},
        )
        assert result == URIRef("http://ex/x")

    def test_object_with_id_and_other_members_is_rdf_data(self, settings):
        # §2.2 rule 3 wins when other members are present: the object is an
        # RDF data form and stays a JSON structure
        form = {"@id": "http://ex/s", "http://ex/p": "v"}
        result = Operation.process_json(settings, form)
        assert result == form


class TestScalarForms:
    def test_string_coerces_to_xsd_string(self, settings):
        result = Operation.process_json(settings, "hello")
        assert result == Literal("hello", datatype=XSD.string)

    def test_integer_coerces_to_xsd_integer(self, settings):
        result = Operation.process_json(settings, 42)
        assert result.datatype == XSD.integer

    def test_fractional_number_coerces_to_xsd_double(self, settings):
        result = Operation.process_json(settings, 3.14)
        assert result.datatype == XSD.double

    def test_boolean_coerces_to_xsd_boolean(self, settings):
        result = Operation.process_json(settings, True)
        assert result.datatype == XSD.boolean

    def test_null_is_invalid(self, settings):
        # §2.2 rule 7 / §3.7: null is not a valid form
        with pytest.raises(TypeError):
            Operation.process_json(settings, None)


class TestOperationCallForm:
    def test_unknown_operation_raises_value_error(self, settings):
        # §3.7: unknown operation name in `@op` → ValueError
        with pytest.raises(ValueError):
            Operation.process_json(settings, {"@op": "NoSuchOperation"})

    def test_execute_is_not_an_operation(self, settings):
        # §4 / §5: the former `Execute` operation was removed from the
        # algebra, so requesting it is an unknown operation → ValueError
        with pytest.raises(ValueError):
            Operation.process_json(
                settings,
                {"@op": "Execute", "args": {"operation": {"@op": "STRUUID"}}},
            )


class TestSequenceScoping:
    def test_variable_visible_to_later_steps(self, settings):
        # §3.4: a variable bound in a program step is visible to subsequent
        # steps of the same sequence
        program = [
            {"@op": "Variable", "args": {"name": "x", "value": "v"}},
            {"@op": "Value", "args": {"name": "$x"}},
        ]
        result = Operation.process_json(settings, program)
        # §3.2: a Variable leaves no item
        assert result == [Literal("v", datatype=XSD.string)]

    def test_variable_visible_in_nested_sequence(self, settings):
        # §3.4: ...and to forms nested within them
        program = [
            {"@op": "Variable", "args": {"name": "x", "value": "v"}},
            [{"@op": "Value", "args": {"name": "$x"}}],
        ]
        result = Operation.process_json(settings, program)
        # §3.1: the nested sequence contributes its items, flat
        assert result == [Literal("v", datatype=XSD.string)]

    def test_binding_ceases_after_sequence_ends(self, settings):
        # §3.4: the binding ceases to exist after the sequence ends
        stack: list = []
        Operation.process_json(
            settings,
            [{"@op": "Variable", "args": {"name": "x", "value": "v"}}],
            variable_stack=stack,
        )
        assert stack == []
        with pytest.raises(ValueError):
            Operation.process_json(
                settings,
                {"@op": "Value", "args": {"name": "$x"}},
                variable_stack=stack,
            )

    def test_sequence_value_is_list_of_element_values(self, settings):
        # §3.2: the sequence's value is the concatenation of element values
        result = Operation.process_json(settings, ["a", 1])
        assert result == [
            Literal("a", datatype=XSD.string),
            Literal(1, datatype=XSD.integer),
        ]


def _table(*values: str) -> JSONResult:
    return JSONResult.from_json(
        {
            "head": {"vars": ["x"]},
            "results": {
                "bindings": [{"x": {"type": "literal", "value": v}} for v in values]
            },
        }
    )


class TestFlatSequences:
    def test_nested_sequences_concatenate(self, settings):
        # §3.1: a sequence is never an item of a sequence
        result = Operation.process_json(settings, [["a", "b"], ["c"]])
        assert result == [
            Literal("a", datatype=XSD.string),
            Literal("b", datatype=XSD.string),
            Literal("c", datatype=XSD.string),
        ]

    def test_deeply_nested_sequences_concatenate(self, settings):
        result = Operation.process_json(settings, [[["a"]], [[], "b"]])
        assert result == [
            Literal("a", datatype=XSD.string),
            Literal("b", datatype=XSD.string),
        ]

    def test_empty_element_sequence_contributes_nothing(self, settings):
        result = Operation.process_json(settings, [[], "a", []])
        assert result == [Literal("a", datatype=XSD.string)]

    def test_variable_leaves_no_item(self, settings):
        # §3.2: a Variable leaves no item, as xsl:variable leaves none
        result = Operation.process_json(
            settings, [{"@op": "Variable", "args": {"name": "x", "value": "v"}}]
        )
        assert result == []

    def test_sequence_valued_operation_contributes_its_items(self, settings):
        # §3.1: an element whose value is a sequence (a ForEach) contributes
        # its items
        result = Operation.process_json(
            settings,
            [
                "a",
                {
                    "@op": "ForEach",
                    "args": {
                        "select": ["b", "c"],
                        "operation": {"@op": "Current", "args": {}},
                    },
                },
            ],
        )
        assert result == [
            Literal("a", datatype=XSD.string),
            Literal("b", datatype=XSD.string),
            Literal("c", datatype=XSD.string),
        ]

    def test_result_is_not_dissolved(self, settings):
        # §3.1: a Result is a value in its own right; concatenation never
        # dissolves it into its rows
        table = _table("a", "b", "c")
        result = Operation.process_json(settings, [table, "z"])
        assert len(result) == 2
        assert isinstance(result[0], Result)
        assert len(list(result[0])) == 3
        assert result[1] == Literal("z", datatype=XSD.string)

    def test_bindings_dissolves_explicitly(self, settings):
        # §3.1: Bindings does the dissolving, explicitly — its rows become
        # items of the enclosing sequence
        table = _table("a", "b")
        result = Operation.process_json(
            settings, [{"@op": "Bindings", "args": {"table": table}}, "z"]
        )
        assert len(result) == 3
