import importlib
import sys

from starlette.testclient import TestClient


def test_returns_synthetic_supplier_offers(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://supplier.example")
    monkeypatch.setenv("INVENTORY_PATH", "data/inventory.json")
    sys.modules.pop("main", None)
    supplier_main = importlib.import_module("main")

    body = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": "msg-test",
                "role": "ROLE_USER",
                "parts": [
                    {"text": "Find BAT-48V-750 for shipment SHP-10042"}
                ],
            }
        },
    }
    with TestClient(supplier_main.app) as client:
        response = client.post(
            "/",
            json=body,
            headers={"A2A-Version": "1.0"},
        )

    assert response.status_code == 200
    assert "Northwind Cells" in response.text
