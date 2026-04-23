from gmail_moneywiz_export.cli import build_query


def test_build_query_adds_default_subject_exclusions() -> None:
    query = build_query("banks-processed")
    assert '-label:banks-processed' in query
    assert '-subject:"Estado de cuenta"' in query
    assert '-subject:"ACTUALIZACIÓN DE DATOS"' in query
