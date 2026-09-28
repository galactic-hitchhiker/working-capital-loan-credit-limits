"""Incremental version of the conservative SEC snapshot extractor.

Each source fact is parsed once per company. Advancing through monthly dates
preserves the filing-date and conflicting-fact rules in sec_data.py.
"""

import math
from dataclasses import asdict
from datetime import date, timedelta

from sec_data import TAGS, eligible_facts, ratio


class FactIndex:
    """Cache one issuer's facts while monthly decision dates advance in order.

    pending holds facts sorted by filing date; position tracks how many have
    been consumed. known groups available facts by field, period end and start,
    retaining the latest filing date and any conflicting facts at that date.
    """

    def __init__(self, document, last_decision):
        self.document = document
        self.pending, self.position, self.known = {}, {}, {}
        self.current = None
        for field in TAGS:
            annual = field in {"revenue", "operating_cashflow", "net_income"}
            facts = list(
                eligible_facts(document, field, last_decision + timedelta(days=1))
            )
            if annual:
                # Accept roughly annual flows, including 52/53-week fiscal years.
                facts = [
                    r
                    for r in facts
                    if r.start
                    and 330
                    <= (date.fromisoformat(r.end) - date.fromisoformat(r.start)).days
                    + 1
                    <= 400
                ]
            else:
                facts = [r for r in facts if r.start is None]
            self.pending[field] = sorted(facts, key=lambda r: r.filed)
            self.position[field], self.known[field] = 0, {}

    def advance(self, decision):
        """Add newly available filings without revisiting earlier source records."""
        if self.current is not None and decision < self.current:
            raise ValueError("FactIndex must advance chronologically")
        self.current = decision
        for field, pending in self.pending.items():
            position = self.position[field]
            # Filing-day information becomes usable on the following day.
            while (
                position < len(pending)
                and pending[position].filed < decision.isoformat()
            ):
                fact = pending[position]
                starts = self.known[field].setdefault(fact.end, {})
                previous_version = starts.get(fact.start)
                if previous_version is None or fact.filed > previous_version[0]:
                    starts[fact.start] = (fact.filed, [fact])
                elif (
                    fact.filed == previous_version[0]
                    and fact not in previous_version[1]
                ):
                    previous_version[1].append(fact)
                position += 1
            self.position[field] = position

    def get(self, field, *, start=None, end=None):
        """Return the latest known fact for a period, or None if it is ambiguous."""
        periods = self.known[field]
        if not periods:
            return None
        if end is None:
            end = max(periods)
        starts = periods.get(end, {})
        candidates = [
            record for key, record in starts.items() if start is None or key == start
        ]
        if not candidates:
            return None
        latest_filed = max(v[0] for v in candidates)
        facts = [
            fact
            for filed, matching_facts in candidates
            if filed == latest_filed
            for fact in matching_facts
        ]
        # Equal-date conflicting totals remain missing; tag priority breaks only
        # ties between facts that agree on the period and value.
        if len({(f.start, f.value) for f in facts}) != 1:
            return None
        return min(facts, key=lambda f: (TAGS[field].index(f.tag), f.accession))

    def snapshot(self, decision):
        """Return period-matched financial values and the source facts behind them."""
        self.advance(decision)
        balance, annual = self.get("assets"), self.get("operating_cashflow")
        facts = {"assets": balance, "operating_cashflow": annual}
        for field in ("current_assets", "current_liabilities", "cash"):
            facts[field] = self.get(field, end=balance.end) if balance else None
        for field in ("revenue", "net_income"):
            facts[field] = (
                self.get(field, start=annual.start, end=annual.end) if annual else None
            )
        # Flow-to-assets ratios use assets at the annual flow's start and end,
        # even if a newer balance sheet is available for liquidity predictors.
        opening = closing = None
        if annual:
            opening = self.get(
                "assets", end=str(date.fromisoformat(annual.start) - timedelta(days=1))
            )
            closing = self.get("assets", end=annual.end)
        average_assets = (
            (opening.value + closing.value) / 2 if opening and closing else None
        )
        values = {k: v.value if v else None for k, v in facts.items()}
        current_assets, current_liabilities, assets = (
            values["current_assets"],
            values["current_liabilities"],
            values["assets"],
        )
        values.update(
            cik=str(self.document["cik"]).zfill(10),
            entity_name=self.document.get("entityName", ""),
            as_of=str(decision),
            currency="USD",
            flow_basis="last_reported_annual_not_TTM",
            balance_period_end=balance.end if balance else None,
            balance_age_days=(
                (decision - date.fromisoformat(balance.end)).days if balance else None
            ),
            flow_period_start=annual.start if annual else None,
            flow_period_end=annual.end if annual else None,
            flow_age_days=(
                (decision - date.fromisoformat(annual.end)).days if annual else None
            ),
            current_ratio=ratio(current_assets, current_liabilities),
            working_capital_to_assets=ratio(
                (
                    current_assets - current_liabilities
                    if current_assets is not None and current_liabilities is not None
                    else None
                ),
                assets,
            ),
            return_on_average_assets=ratio(values["net_income"], average_assets),
            operating_cashflow_to_average_assets=ratio(
                values["operating_cashflow"], average_assets
            ),
            log_assets=math.log(assets) if assets is not None and assets > 0 else None,
            status="financial_snapshot_only_no_event_label_or_credit_recommendation",
        )
        facts["opening_assets_for_profitability"] = opening
        facts["closing_assets_for_profitability"] = closing
        return values, {k: asdict(v) if v else None for k, v in facts.items()}
