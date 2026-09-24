from domain import load_demo_data, parse_offers, parse_policy, resolve_shipment
from planner import build_recovery_options, recommend_option


def test_recommends_lowest_cost_compliant_option():
    data = load_demo_data("data/shipments.json")
    shipment = resolve_shipment("Recover SHP-10042", data)
    policy = parse_policy(data["mock_policy"])
    offers = parse_offers({"offers": data["mock_supplier_offers"]})

    options = build_recovery_options(shipment, policy, offers)
    recommendation = recommend_option(options)

    assert recommendation.name == "Split incumbent + Alpine Energy"
    assert recommendation.units_by_launch == 1000
    assert recommendation.incremental_cost == 7800
    assert recommendation.policy_compliant is True


def test_incumbent_only_preserves_partial_units_by_launch():
    data = load_demo_data("data/shipments.json")
    shipment = resolve_shipment("SHP-10042", data)
    policy = parse_policy(data["mock_policy"])
    offers = parse_offers({"offers": data["mock_supplier_offers"]})

    options = build_recovery_options(shipment, policy, offers)
    waiting = next(
        option
        for option in options
        if option.name == "Use incumbent deliveries only"
    )

    assert waiting.policy_compliant is False
    assert waiting.units_by_launch == 400
    assert waiting.eta.isoformat() == "2026-10-16"


def test_approval_is_derived_from_option_cost():
    data = load_demo_data("data/shipments.json")
    shipment = resolve_shipment("SHP-10042", data)
    policy = parse_policy(data["mock_policy"])
    offers = parse_offers({"offers": data["mock_supplier_offers"]})

    options = build_recovery_options(shipment, policy, offers)
    recommendation = recommend_option(options)

    assert recommendation.director_approval_required is False
