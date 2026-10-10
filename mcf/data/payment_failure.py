"""Recurrent payment-failure and bankruptcy/receivership disclosure episodes.

This is a library used by mcf.data.empirical, not a command-line entry point.
Episodes are defined by a configurable quiet gap between qualifying disclosures.
The quiet gap is an operational disclosure rule, not evidence of contractual cure.
"""

from collections import Counter
from datetime import date, timedelta

from mcf.data.sec import filing_items

TARGET = "disclosed_payment_failure_within_60_days"
BANKRUPTCY_PAYMENT_TARGET = "disclosed_bankruptcy_or_payment_failure_within_60_days"
RECURRENT_TARGETS = {TARGET, BANKRUPTCY_PAYMENT_TARGET}
REVIEW_TARGET = "disclosed_payment_failure"


def _has_payment_evidence(row, review):
    return (
        row.get("classification") == "QUALIFIED_DEFAULT"
        and review.get("classification") == "QUALIFIED_DEFAULT"
        and review.get("event_type") == "PAYMENT_FAILURE"
        and review.get("certainty") == "HIGH"
        and bool(review.get("evidence_quotes"))
    )


def _assign_episodes(company, target, events, gap_days, counts):
    last = None
    episode_id = episode_start = None
    for event in events:
        filed = date.fromisoformat(event["filingDate"])
        is_start = last is None or (filed - last).days > gap_days
        if is_start:
            episode_start = event["filingDate"]
            episode_id = f"{company}:{target}:{episode_start}"
            counts["episodes"] += 1
        event.update(
            episode_id=episode_id,
            episode_start=episode_start,
            is_episode_start=is_start,
        )
        last = filed


def payment_disclosures(company, filings, reviews, episode_gap_days, include_item_103=False):
    """Build recurrent events; optional composite automatically includes Item 1.03."""
    target = BANKRUPTCY_PAYMENT_TARGET if include_item_103 else TARGET
    events, unresolved, counts = [], [], Counter()
    for filing in sorted(filings, key=lambda f: (f["filingDate"], f["accessionNumber"])):
        items = filing_items(filing["items"])
        if filing["form"] not in {"8-K", "8-K/A"} or not items & {"1.03", "2.04"}:
            continue
        row = reviews.get((company, filing["accessionNumber"]))
        saved = (row or {}).get("llm_review", {})
        review = saved.get("review", {})
        if include_item_103 and "1.03" in items:
            counts["item_103_automatic"] += 1
            payment_evidence = "2.04" in items and _has_payment_evidence(
                row or {}, review
            )
            events.append(
                dict(
                    filing,
                    target=target,
                    event_component=(
                        "ITEM_1_03_AND_QUALIFIED_ITEM_2_04"
                        if payment_evidence else "ITEM_1_03"
                    ),
                    review_definition="sec_item_1_03",
                    item_204_classification=(
                        (row or {}).get("classification", "") if "2.04" in items else ""
                    ),
                    item_204_event_type=(
                        review.get("event_type", "") if "2.04" in items else ""
                    ),
                    item_204_payment_evidence=payment_evidence,
                    item_204_review_status=(row or {}).get("llm_status", ""),
                )
            )
            continue
        if row and row.get("filingDate") not in {None, "", filing["filingDate"]}:
            raise ValueError(f"Payment disclosure date mismatch: {company} {filing['accessionNumber']}")
        classification = (row or {}).get("classification", "MANUAL_REVIEW")
        counts["missing_review" if row is None else classification.lower()] += 1
        review_target = (saved.get("settings") or {}).get("target")
        legacy = row is not None and review_target is None
        if legacy and (saved.get("provider") != "openai_batch" or "2.04" not in items):
            raise ValueError("Only earlier OpenAI Item 2.04 reviews can be reused as legacy evidence")
        if row is not None and review_target not in {None, REVIEW_TARGET}:
            raise ValueError("Incompatible payment-failure review target")
        if legacy:
            counts["legacy_item_204_reviews"] += 1
        if classification == "MANUAL_REVIEW":
            unresolved.append(filing)
            continue
        if review.get("classification") != classification:
            raise ValueError("Saved review and exported classification disagree")
        if not review.get("evidence_quotes") or review.get("certainty") != "HIGH":
            raise ValueError("Resolved payment-failure review requires high certainty and evidence")
        if classification == "NON_DEFAULT":
            if review.get("event_type") != "BENIGN":
                raise ValueError("Payment-negative review must have BENIGN event type")
            if legacy:
                counts["legacy_non_default_reused"] += 1
            continue
        if legacy and classification == "QUALIFIED_DEFAULT" and review.get("event_type") in {"ACCELERATION", "ENFORCEMENT"}:
            # Broader distress does not establish either missed payment or its absence.
            unresolved.append(filing)
            counts["legacy_non_payment_unresolved"] += 1
            continue
        if classification != "QUALIFIED_DEFAULT" or review.get("event_type") != "PAYMENT_FAILURE":
            raise ValueError("Only explicit PAYMENT_FAILURE qualifies for this target")
        if legacy:
            counts["legacy_payment_failure_reused"] += 1
        if "1.03" in items and "2.04" in items:
            component = "ITEM_1_03_AND_QUALIFIED_ITEM_2_04"
        elif "1.03" in items:
            component = "ITEM_1_03"
        else:
            component = "QUALIFIED_ITEM_2_04"
        events.append(
            dict(
                filing,
                target=target,
                event_component=component,
                review_definition="legacy_item_204" if legacy else REVIEW_TARGET,
                item_204_classification=classification if "2.04" in items else "",
                item_204_event_type="PAYMENT_FAILURE",
                item_204_payment_evidence=True,
                item_204_review_status=row.get("llm_status", ""),
            )
        )
    _assign_episodes(company, target, events, episode_gap_days, counts)
    counts["payment_failure_disclosures"] = len(events)
    if include_item_103:
        counts["payment_failure_disclosures"] = sum(bool(e["item_204_payment_evidence"]) for e in events)
        counts["combined_disclosures"] = len(events)
    return events, unresolved, counts


def episode_label(decision, events, unresolved, last_issuer_date, cutoff, gap_days):
    """Label the next disclosure episode within 60 days, using past-only eligibility.

    A recent known disclosure excludes the row for the configured gap. All
    unresolved earlier filings exclude later rows until their reviews are resolved.
    Future unresolved evidence censors its horizon, rather than creating negatives.
    """
    horizon = decision + timedelta(days=60)
    past = [date.fromisoformat(e["filingDate"]) for e in events if e["filingDate"] <= str(decision)]
    if past and (decision - max(past)).days <= gap_days:
        return None, "payment_episode_washout", None
    unknown = sorted(date.fromisoformat(e["filingDate"]) for e in unresolved)
    if unknown and unknown[0] <= decision:
        return None, "post_unresolved_payment_disclosure", None
    if horizon + timedelta(days=1) >= cutoff:
        return None, "cutoff_censoring", None
    upcoming = next((e for e in events if e["is_episode_start"] and decision < date.fromisoformat(e["filingDate"]) <= horizon), None)
    if upcoming and (not unknown or date.fromisoformat(upcoming["filingDate"]) <= unknown[0]):
        return 1, "observed_payment_failure_disclosure", upcoming
    if unknown and unknown[0] <= horizon:
        return None, "unresolved_payment_disclosure_in_window", None
    if last_issuer_date < horizon:
        return None, "issuer_followup_censoring", None
    return 0, "no_disclosed_payment_failure_in_observed_window", None
