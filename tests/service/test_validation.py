"""What the service tells a client about a document before running it.

These tests are about the service layer, not the language, so unlike
tests/unit/ they may name implementation modules.
"""

from web_algebra.operation import OperationKind
from web_algebra.validation import summarize, validate


def test_a_well_formed_plan_validates():
    plan = [
        {
            "@op": "SELECT",
            "args": {
                "endpoint": {"@id": "https://query.wikidata.org/sparql"},
                "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 1",
            },
        }
    ]

    assert validate(plan).valid


def test_a_single_operation_is_a_plan_of_one():
    form = {"@op": "Str", "args": {"input": "x"}}

    assert validate(form).valid
    assert [summary.index for summary in summarize(form)] == [0]


def test_an_unknown_operation_is_reported_with_its_path():
    plan = [{"@op": "NotAnOperation", "args": {}}]

    result = validate(plan)

    assert not result.valid
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].path == "/0"
    assert result.diagnostics[0].op == "NotAnOperation"
    assert "NotAnOperation" in result.diagnostics[0].message


def test_a_missing_required_argument_is_reported():
    plan = [{"@op": "SELECT", "args": {"query": "SELECT * WHERE { ?s ?p ?o }"}}]

    result = validate(plan)

    assert not result.valid
    assert result.diagnostics[0].path == "/0/args"
    assert "endpoint" in result.diagnostics[0].message


def test_nested_operations_are_validated_too():
    plan = [
        {
            "@op": "ForEach",
            "args": {
                "select": {"@op": "NotAnOperation", "args": {}},
                "operation": {"@op": "Str", "args": {"input": "x"}},
            },
        }
    ]

    result = validate(plan)

    assert not result.valid
    assert result.diagnostics[0].path == "/0/args/select"


def test_operations_embedded_in_json_ld_are_validated():
    plan = [
        {
            "@op": "PUT",
            "args": {
                "url": {"@id": "https://localhost:4443/districts/x/"},
                "data": {
                    "@id": "https://localhost:4443/districts/x/#this",
                    "http://purl.org/dc/terms/title": {
                        "@op": "NotAnOperation",
                        "args": {},
                    },
                },
            },
        }
    ]

    result = validate(plan)

    assert not result.valid
    assert result.diagnostics[0].op == "NotAnOperation"


def test_reads_writes_and_destructive_operations_are_told_apart():
    plan = [
        {
            "@op": "SELECT",
            "args": {"endpoint": {"@id": "https://dbpedia.org/sparql"}, "query": "ASK {}"},
        },
        {
            "@op": "ldh-AddResultSetChart",
            "args": {"url": {"@id": "https://localhost:4443/districts/"}},
        },
        {
            "@op": "PATCH",
            "args": {
                "url": {"@id": "https://localhost:4443/districts/x/"},
                "update": "DELETE WHERE { ?s ?p ?o }",
            },
        },
    ]

    kinds = [summary.kind for summary in summarize(plan)]

    assert kinds == [
        OperationKind.READ,
        OperationKind.WRITE,
        OperationKind.DESTRUCTIVE,
    ]


def test_a_control_form_takes_the_kind_of_its_body_and_names_it():
    plan = [
        {
            "@op": "ForEach",
            "args": {
                "select": {
                    "@op": "SELECT",
                    "args": {
                        "endpoint": {"@id": "https://query.wikidata.org/sparql"},
                        "query": "SELECT * WHERE { ?s ?p ?o }",
                    },
                },
                "operation": {
                    "@op": "PATCH",
                    "args": {
                        "url": {"@op": "Value", "args": {"name": "district"}},
                        "update": "INSERT { } WHERE { }",
                    },
                },
            },
        }
    ]

    summary = summarize(plan)[0]

    assert summary.op == "ForEach"
    assert summary.via == "PATCH"
    assert summary.kind is OperationKind.DESTRUCTIVE


def test_the_summary_reports_the_address_the_plan_names():
    plan = [
        {
            "@op": "SELECT",
            "args": {
                "endpoint": {"@id": "https://query.wikidata.org/sparql"},
                "query": "SELECT * WHERE { ?s ?p ?o }",
            },
        }
    ]

    assert summarize(plan)[0].target == "https://query.wikidata.org/sparql"


def test_a_computed_address_is_reported_as_unknown_rather_than_guessed():
    plan = [
        {
            "@op": "PATCH",
            "args": {
                "url": {"@op": "Value", "args": {"name": "district"}},
                "update": "INSERT { } WHERE { }",
            },
        }
    ]

    assert summarize(plan)[0].target is None
