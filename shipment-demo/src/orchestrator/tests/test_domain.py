import pytest

from domain import load_demo_data, resolve_shipment


def test_uses_default_shipment_when_id_is_omitted():
    data = load_demo_data("data/shipments.json")
    shipment = resolve_shipment("Help with the delayed battery shipment", data)
    assert shipment.shipment_id == "SHP-10042"


def test_rejects_unknown_shipment():
    data = load_demo_data("data/shipments.json")
    with pytest.raises(ValueError, match="Unknown shipment ID"):
        resolve_shipment("Recover SHP-99999", data)
