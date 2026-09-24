from __future__ import annotations

from itertools import combinations

from domain import PolicyDecision, RecoveryOption, Shipment, SupplierOffer


def build_recovery_options(
    shipment: Shipment,
    policy: PolicyDecision,
    offers: list[SupplierOffer],
) -> list[RecoveryOption]:
    options: list[RecoveryOption] = [
        RecoveryOption(
            name="Use incumbent deliveries only",
            units_by_launch=shipment.incumbent_partial_units,
            eta=shipment.delayed_eta,
            incremental_cost=0,
            policy_compliant=False,
            director_approval_required=False,
            explanation=(
                f"{shipment.incumbent_partial_units} units arrive by "
                f"{shipment.incumbent_partial_eta}; the remaining units do not "
                f"arrive until {shipment.delayed_eta}."
            ),
        )
    ]

    eligible = [
        offer
        for offer in offers
        if offer.part_number == shipment.part_number
        and offer.quality_status.lower() == "approved"
        and offer.eta <= shipment.launch_date
    ]
    for count in range(1, len(eligible) + 1):
        for selected in combinations(eligible, count):
            units = shipment.incumbent_partial_units + sum(
                offer.available_units for offer in selected
            )
            incremental_cost = sum(
                (offer.unit_cost - shipment.incumbent_unit_cost)
                * offer.available_units
                + offer.expedite_fee
                for offer in selected
            )
            max_expedite = max(offer.expedite_fee for offer in selected)
            compliant = (
                policy.alternate_supplier_allowed
                and policy.split_shipment_allowed
                and units >= policy.minimum_units_by_launch
                and incremental_cost <= policy.max_incremental_cost
                and max_expedite <= policy.max_expedite_fee
            )
            approval = incremental_cost > policy.max_incremental_cost
            supplier_names = " + ".join(offer.supplier_id for offer in selected)
            eta = max(
                [shipment.incumbent_partial_eta]
                + [offer.eta for offer in selected]
            )
            options.append(
                RecoveryOption(
                    name=f"Split incumbent + {supplier_names}",
                    units_by_launch=units,
                    eta=eta,
                    incremental_cost=round(incremental_cost, 2),
                    policy_compliant=compliant,
                    director_approval_required=approval,
                    explanation=(
                        f"{shipment.incumbent_partial_units} incumbent units plus "
                        f"{sum(o.available_units for o in selected)} alternate "
                        f"units arrive by {eta}."
                    ),
                )
            )
    return sorted(
        options,
        key=lambda item: (
            not item.policy_compliant,
            -item.units_by_launch,
            item.incremental_cost,
            item.eta,
        ),
    )


def recommend_option(options: list[RecoveryOption]) -> RecoveryOption:
    compliant = [option for option in options if option.policy_compliant]
    if not compliant:
        return options[0]
    return min(
        compliant,
        key=lambda item: (
            item.incremental_cost,
            -item.units_by_launch,
            item.eta,
        ),
    )
