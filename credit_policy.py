"""Chapter 5 research policy. Monetary inputs must share one currency.

No parameter is fitted or claimed to be an industry standard. The risk estimate
must come from a separately validated model or be explicitly marked illustrative.
Annual inputs represent one consistent reported year or a reconstructed TTM.
"""

from dataclasses import asdict, dataclass
from math import exp, isfinite


def nonnegative(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be a finite nonnegative number")


@dataclass(frozen=True)
class PolicyConfig:
    revenue_fraction: float = 0.20
    cashflow_fraction: float = 0.50
    cash_fraction: float = 0.10
    risk_sensitivity: float = 10.0
    increase_smoothing: float = 0.50
    monthly_increase_cap: float = 0.10
    increase_deadband: float = 0.02

    def __post_init__(self):
        for name, value in asdict(self).items():
            nonnegative(name, value)
        for name in (
            "revenue_fraction",
            "cashflow_fraction",
            "cash_fraction",
            "increase_smoothing",
            "monthly_increase_cap",
            "increase_deadband",
        ):
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must not exceed one")


@dataclass(frozen=True)
class PolicyInputs:
    revenue_annual: float
    operating_cashflow_annual: float
    eligible_cash: float
    external_debt_service_60d: float
    risk_probability: float
    hard_cap: float
    outstanding_exposure: float
    previous_limit: float | None = None
    information_changed: bool = True
    hard_stop: bool = False
    currency: str = "USD"
    risk_target: str = "illustrative_event"
    risk_horizon_days: int = 60
    risk_is_illustrative: bool = True

    def __post_init__(self):
        for name in (
            "revenue_annual",
            "eligible_cash",
            "external_debt_service_60d",
            "risk_probability",
            "hard_cap",
            "outstanding_exposure",
        ):
            nonnegative(name, getattr(self, name))
        if self.previous_limit is not None:
            nonnegative("previous_limit", self.previous_limit)
        if (
            isinstance(self.operating_cashflow_annual, bool)
            or not isinstance(self.operating_cashflow_annual, (int, float))
            or not isfinite(self.operating_cashflow_annual)
        ):
            raise ValueError("operating_cashflow_annual must be finite")
        if self.risk_probability > 1:
            raise ValueError("risk_probability must be in [0, 1]")
        if type(self.risk_horizon_days) is not int or self.risk_horizon_days <= 0:
            raise ValueError("risk_horizon_days must be a positive integer")
        for name in ("information_changed", "hard_stop", "risk_is_illustrative"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if not self.currency or not self.risk_target:
            raise ValueError("Currency and target must be explicit")


@dataclass(frozen=True)
class PolicyResult:
    revenue_cap: float
    cashflow_cash_cap: float
    capacity: float
    risk_multiplier: float
    risk_adjusted_capacity: float
    raw_limit: float
    assigned_limit: float
    available_credit: float
    excess_exposure: float
    binding_constraint: str
    update_reason: str


def determine_limit(x: PolicyInputs, c: PolicyConfig = PolicyConfig()) -> PolicyResult:
    """Apply one review using additional external debt payments due in 60 days.

    external_debt_service_60d excludes target-facility principal and any payment
    already reflected in the cash-flow capacity estimate. In particular, do not
    deduct cash interest again when it is already included in operating cash flow.

    The raw limit caps total target-facility exposure; existing target-facility
    drawings are subtracted only to determine NEW available credit. All decreases
    take effect immediately. Without a documented information change, increases
    are held. Zero-limit accounts require a fresh initial assessment (None).
    """
    revenue_cap = c.revenue_fraction * x.revenue_annual / 6.0
    cashflow_cash_cap = (
        c.cashflow_fraction * max(x.operating_cashflow_annual, 0) / 6.0
        + c.cash_fraction * x.eligible_cash
    )
    capacity = max(
        0.0, min(revenue_cap, cashflow_cash_cap) - x.external_debt_service_60d
    )
    multiplier = exp(-c.risk_sensitivity * x.risk_probability)
    adjusted = capacity * multiplier
    raw = min(x.hard_cap, adjusted)
    binding = "hard_cap" if x.hard_cap < adjusted else "risk_adjusted_capacity"
    if capacity == 0:
        binding = "zero_capacity"
    previous = x.previous_limit
    if x.hard_stop:
        raw = assigned = 0.0
        reason = binding = "hard_stop"
    elif previous is None:
        assigned, reason = raw, "initial_assessment"
    elif raw < previous:
        assigned, reason = raw, "immediate_reduction"
    elif raw == previous:
        assigned, reason = previous, "unchanged"
    elif previous == 0:
        assigned, reason = 0.0, "reopening_requires_initial_assessment"
    elif not x.information_changed:
        assigned, reason = previous, "no_new_information"
    elif raw - previous <= c.increase_deadband * previous:
        assigned, reason = previous, "increase_below_deadband"
    else:
        assigned = min(
            raw,
            previous + c.increase_smoothing * (raw - previous),
            (1 + c.monthly_increase_cap) * previous,
        )
        reason = "phased_increase"
    return PolicyResult(
        revenue_cap,
        cashflow_cash_cap,
        capacity,
        multiplier,
        adjusted,
        raw,
        assigned,
        max(0.0, assigned - x.outstanding_exposure),
        max(0.0, x.outstanding_exposure - assigned),
        binding,
        reason,
    )


def expected_loss_amount(
    *,
    pd: float,
    lgd: float,
    ead: float,
    pd_horizon_days: int,
    exposure_horizon_days: int = 60,
    target: str = "default",
) -> float:
    """Optional scenario only; forbids distress-as-PD and silent horizon conversion."""
    if target != "default" or pd_horizon_days != exposure_horizon_days:
        raise ValueError("Expected loss needs a default PD at the exposure horizon")
    for name, value in (("pd", pd), ("lgd", lgd), ("ead", ead)):
        nonnegative(name, value)
    if (
        pd > 1
        or lgd > 1
        or type(pd_horizon_days) is not int
        or pd_horizon_days <= 0
        or type(exposure_horizon_days) is not int
        or exposure_horizon_days <= 0
    ):
        raise ValueError("Invalid probability, LGD or horizon")
    return pd * lgd * ead
