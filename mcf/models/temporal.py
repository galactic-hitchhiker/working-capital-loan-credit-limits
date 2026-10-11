"""Chapter 3/4 helpers for VERIFIED labels and chronological data boundaries.

These helpers do not discover credit events or establish observation coverage.
Those inputs need an independently reviewed event register and coverage record.
No machine-learning fitting or performance claim is made by this module.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class LabeledObservation:
    """A company-month outcome with its horizon and first usable label date."""

    company_id: str
    decision_date: date
    horizon_end: date
    label_available_on: date
    label: int


def make_label(
    *,
    company_id: str,
    decision_date: date,
    horizon_days: int,
    observed_through: date,
    coverage_verified: bool,
    coverage_known_on: date | None = None,
    event_date: date | None = None,
    event_verified: bool = False,
    event_known_on: date | None = None,
    event_source: str = "",
):
    """Event interval is (decision_date, horizon_end], with full follow-up.

    coverage_verified means a defensible source establishes event/no-event
    coverage for this company's entire outcome window. No 8-K found is NOT proof.
    coverage_known_on records when that complete follow-up became available.
    Return None for incomplete coverage, unresolved event candidates, or post-event
    observations. Require a fixed event definition outside this function.
    """
    if type(horizon_days) is not int or horizon_days <= 0 or not company_id:
        raise ValueError("Company ID and a positive integer horizon are required")
    end = decision_date + timedelta(days=horizon_days)
    if not coverage_verified or observed_through < end or coverage_known_on is None:
        return None
    if coverage_known_on < end:
        raise ValueError("Complete follow-up cannot be known before the horizon ends")
    if event_date is not None:
        if not event_verified or event_known_on is None or not event_source:
            return None
        if event_known_on < event_date:
            raise ValueError("An actual event cannot be known before it occurs")
        if event_date <= decision_date:
            return None
    positive = event_date is not None and event_date <= end
    # Full outcome window plus a conservative next-day availability convention.
    available = max(end, coverage_known_on) + timedelta(days=1)
    if positive:
        available = max(available, event_known_on + timedelta(days=1))
    return LabeledObservation(company_id, decision_date, end, available, int(positive))


def chronological_partition(
    observations,
    *,
    tuning_start: date,
    calibration_start: date,
    selection_start: date,
    test_start: date,
    observed_as_of: date,
    calibration_end: date | None = None,
):
    """Five stages with horizon/availability purging; no random row splitting.

    Boundaries are inclusive for the following stage and must be month starts.
    Fit/calibration/selection labels must be known strictly before the next stage.
    An optional calibration_end excludes decisions until selection_start and
    purges calibration labels unavailable before that excluded interval.
    Returns purged observations explicitly; callers must audit event counts before
    fitting and must not move boundaries in response to final-test model scores.
    """
    boundaries = [tuning_start, calibration_start, selection_start, test_start]
    if boundaries != sorted(set(boundaries)) or any(d.day != 1 for d in boundaries):
        raise ValueError("Stage boundaries must be increasing distinct month starts")
    if observed_as_of <= test_start:
        raise ValueError("Observation cutoff must be after test start")
    if calibration_end is None:
        calibration_end = selection_start
    if (
        calibration_end.day != 1
        or not calibration_start < calibration_end <= selection_start
    ):
        raise ValueError("Invalid calibration end")
    has_gap = calibration_end < selection_start
    names = ["training", "tuning", "calibration", "selection", "test"]
    result = {name: [] for name in names + ["purged"] + (["excluded"] if has_gap else [])}
    seen = set()
    for row in observations:
        key = (row.company_id, row.decision_date)
        if key in seen:
            raise ValueError("Duplicate company-decision-date observation")
        seen.add(key)
        if (
            row.label not in (0, 1)
            or row.horizon_end <= row.decision_date
            or row.label_available_on <= row.horizon_end
        ):
            raise ValueError("Invalid label timing or outcome")
        if has_gap and calibration_end <= row.decision_date < selection_start:
            result["excluded"].append(row)
            continue
        # Count crossed boundaries to locate the decision's chronological stage.
        stage = sum(row.decision_date >= b for b in boundaries)
        if stage == 2:
            cutoff = calibration_end
        else:
            cutoff = boundaries[stage] if stage < 4 else observed_as_of
        if row.label_available_on >= cutoff:
            result["purged"].append(row)
        else:
            result[names[stage]].append(row)
    return result
