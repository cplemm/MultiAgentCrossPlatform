import pytest

from specialists import extract_supplier_payload


def test_extracts_supplier_artifact_text():
    payload = '{"offers":[{"supplier_id":"Northwind Cells"}]}'
    response = {
        "result": {
            "task": {
                "artifacts": [
                    {"parts": [{"text": payload}]}
                ]
            }
        }
    }
    assert (
        extract_supplier_payload(response)["offers"][0]["supplier_id"]
        == "Northwind Cells"
    )


def test_rejects_empty_supplier_artifact():
    response = {"result": {"task": {"artifacts": []}}}
    with pytest.raises(RuntimeError, match="no artifact text"):
        extract_supplier_payload(response)
