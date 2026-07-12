"""Spec: formal-semantics.md §2 (Document Model) and §3 (Evaluation Semantics).

Covers the envelope (§2.1), form discrimination and scalar coercion (§2.2),
the URI reference form, and sequence/variable scoping (§3.2, §3.4).
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestEnvelope:
    def test_envelope_unwraps_program(self):
        # §2.1: the `program` member holds the form(s) to evaluate
        doc = {"@web-algebra": "1", "program": [{"@op": "STRUUID"}]}
        assert Operation.unwrap_document(doc) == [{"@op": "STRUUID"}]

    def test_envelope_without_program_raises(self):
        # §2.1/§3.7: an envelope without a `program` member is invalid
        with pytest.raises(ValueError):
            Operation.unwrap_document({"@web-algebra": "1"})

    def test_informative_members_are_ignored(self):
        # §2.1: `name`/`description` are informative; unknown members ignored
        doc = {
            "@web-algebra": "1",
            "name": "x",
            "description": "y",
            "future-member": True,
            "program": [],
        }
        assert Operation.unwrap_document(doc) == []

    def test_bare_document_passes_through(self):
        # §2.1: the envelope is optional; bare forms remain valid
        bare = [{"@op": "STRUUID"}]
        assert Operation.unwrap_document(bare) is bare


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


class TestSequenceScoping:
    def test_variable_visible_to_later_steps(self, settings):
        # §3.4: a variable bound in a program step is visible to subsequent
        # steps of the same sequence
        program = [
            {"@op": "Variable", "args": {"name": "x", "value": "v"}},
            {"@op": "Value", "args": {"name": "$x"}},
        ]
        result = Operation.process_json(settings, program)
        assert result == [None, Literal("v", datatype=XSD.string)]

    def test_variable_visible_in_nested_sequence(self, settings):
        # §3.4: ...and to forms nested within them
        program = [
            {"@op": "Variable", "args": {"name": "x", "value": "v"}},
            [{"@op": "Value", "args": {"name": "$x"}}],
        ]
        result = Operation.process_json(settings, program)
        assert result[1] == [Literal("v", datatype=XSD.string)]

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
        # §3.2: the sequence's value is the Sequence of element values
        result = Operation.process_json(settings, ["a", 1])
        assert result == [
            Literal("a", datatype=XSD.string),
            Literal(1, datatype=XSD.integer),
        ]
