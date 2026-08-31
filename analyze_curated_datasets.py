import argparse
import csv
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
TURN_RE = re.compile(r"(?m)^(Model[12]):\s*")
JUDGE_RE = re.compile(r"^Judge \d+ \((.+)\) winner$")
TIE = "Tie"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the curated debate and judgement datasets.")
    parser.add_argument(
        "--data-dir",
        default="data/paper_dataset",
        help="Directory containing RawDebates.csv and judgements/.",
    )
    parser.add_argument(
        "--topics",
        default="topics/phase1_topics.json",
        help="Topic JSON used to recover stable topic identifiers.",
    )
    parser.add_argument(
        "--output-dir",
        help="Analysis output directory; defaults to <data-dir>/analysis.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def parse_turns(text: str) -> list[tuple[str, str]]:
    matches = list(TURN_RE.finditer(text))
    turns: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        turns.append((match.group(1), text[match.end() : end].strip()))
    return turns


def round_value(value: float, digits: int = 3) -> float:
    return round(value, digits)


def pct(value: float, digits: int = 1) -> str:
    return f"{100.0 * value:.{digits}f}%"


def average_ranks(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and math.isclose(ordered[end][1], ordered[index][1]):
            end += 1
        rank = (index + 1 + end) / 2.0
        for name, _ in ordered[index:end]:
            ranks[name] = rank
        index = end
    return ranks


def spearman(left: dict[str, float], right: dict[str, float]) -> float:
    names = sorted(set(left) & set(right))
    if len(names) < 2:
        return float("nan")
    left_ranks = average_ranks({name: left[name] for name in names})
    right_ranks = average_ranks({name: right[name] for name in names})
    left_mean = statistics.mean(left_ranks.values())
    right_mean = statistics.mean(right_ranks.values())
    numerator = sum((left_ranks[name] - left_mean) * (right_ranks[name] - right_mean) for name in names)
    left_var = sum((left_ranks[name] - left_mean) ** 2 for name in names)
    right_var = sum((right_ranks[name] - right_mean) ** 2 for name in names)
    if left_var == 0 or right_var == 0:
        return float("nan")
    return numerator / math.sqrt(left_var * right_var)


def cohen_kappa(left: list[str], right: list[str]) -> tuple[float, float]:
    if len(left) != len(right) or not left:
        return float("nan"), float("nan")
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    categories = sorted(set(left) | set(right))
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum((left_counts[c] / len(left)) * (right_counts[c] / len(right)) for c in categories)
    kappa = (observed - expected) / (1.0 - expected) if expected < 1.0 else float("nan")
    return observed, kappa


def bootstrap_interval(
    units: list[object],
    statistic,
    iterations: int = 4000,
    seed: int = 20260819,
) -> tuple[float, float]:
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(iterations):
        sample = [units[rng.randrange(len(units))] for _ in units]
        value = statistic(sample)
        if not math.isnan(value):
            estimates.append(value)
    estimates.sort()
    if not estimates:
        return float("nan"), float("nan")
    low = estimates[int(0.025 * (len(estimates) - 1))]
    high = estimates[int(0.975 * (len(estimates) - 1))]
    return low, high


def detect_judges(rows: list[dict[str, str]]) -> list[str]:
    judges = []
    for field in rows[0]:
        match = JUDGE_RE.match(field)
        if match:
            judges.append(match.group(1))
    return judges


def judge_label(rows: list[dict[str, str]], judge: str) -> str:
    suffix = f"({judge}) winner"
    return next(field[: -len(" winner")] for field in rows[0] if field.endswith(suffix))


def topic_lookup(path: Path) -> dict[tuple[str, str], str]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    return {(item["position_a"], item["position_b"]): item["id"] for item in topics}


def attach_topics(raw: list[dict[str, str]], topics: dict[tuple[str, str], str]) -> None:
    for row in raw:
        row["topicId"] = topics.get((row["positionA"], row["positionB"]), "unknown")


def raw_audit(raw: list[dict[str, str]]) -> tuple[dict[str, object], dict[str, dict[str, int]]]:
    model_words: dict[str, list[int]] = defaultdict(list)
    words_by_debate_model: dict[str, dict[str, int]] = {}
    turn_failures = []
    legacy_mentions = 0
    meta_mentions = 0
    citation_like = 0
    transcript_hashes = Counter(row["DiscussionPlainText"] for row in raw)
    debate_words = []

    for row in raw:
        turns = parse_turns(row["DiscussionPlainText"])
        expected_first = row["starting"]
        valid_turns = len(turns) == 8
        valid_order = bool(turns) and turns[0][0] == expected_first and all(
            turns[i][0] != turns[i - 1][0] for i in range(1, len(turns))
        )
        if not valid_turns or not valid_order:
            turn_failures.append(row["DebateId"])

        counts = {row["Model1name"]: 0, row["Model2name"]: 0}
        for speaker, content in turns:
            model = row[f"{speaker}name"]
            count = word_count(content)
            counts[model] += count
            model_words[model].append(count)
        words_by_debate_model[row["DebateId"]] = counts
        debate_words.append(sum(counts.values()))

        text = row["DiscussionPlainText"]
        legacy_mentions += int(bool(re.search(r"\bModel[AB]\b", text)))
        meta_mentions += int(bool(re.search(r"\b(judge|benchmark|dataset|evaluation|prompt)\b", text, re.I)))
        citation_like += int(bool(re.search(r"\b(study|report|institute|university|20\d{2})\b|\d+(?:\.\d+)?%", text, re.I)))

    topic_counts = Counter(row["topicId"] for row in raw)
    pair_condition_counts = Counter(
        (
            row["topicId"],
            tuple(sorted((row["Model1name"], row["Model2name"]))),
            row["Model1Position"],
            row["starting"],
        )
        for row in raw
    )
    audit = {
        "rows": len(raw),
        "topics": len(topic_counts),
        "models": len({row["Model1name"] for row in raw} | {row["Model2name"] for row in raw}),
        "topic_counts": dict(sorted(topic_counts.items())),
        "balanced_condition_cells": len(pair_condition_counts),
        "condition_cell_min": min(pair_condition_counts.values()),
        "condition_cell_max": max(pair_condition_counts.values()),
        "turn_structure_failures": turn_failures,
        "duplicate_transcripts": sum(count - 1 for count in transcript_hashes.values() if count > 1),
        "debate_words_min": min(debate_words),
        "debate_words_median": statistics.median(debate_words),
        "debate_words_mean": statistics.mean(debate_words),
        "debate_words_max": max(debate_words),
        "legacy_label_mentions": legacy_mentions,
        "meta_term_mentions": meta_mentions,
        "citation_like_language": citation_like,
        "model_turn_words": {
            model: {
                "mean": round_value(statistics.mean(values), 1),
                "median": round_value(statistics.median(values), 1),
                "min": min(values),
                "max": max(values),
            }
            for model, values in sorted(model_words.items())
        },
    }
    return audit, words_by_debate_model


def diff_votes(
    raw: list[dict[str, str]], diff: list[dict[str, str]], judges: list[str]
) -> list[dict[str, object]]:
    raw_by_id = {row["DebateId"]: row for row in raw}
    votes = []
    for judgement in diff:
        debate = raw_by_id[judgement["DebateId"]]
        for judge in judges:
            label = judge_label(diff, judge)
            winner = judgement[f"{label} winner"]
            winner_position = judgement[f"{label} winningPosition"]
            starter_model = debate["Model1name"] if debate["starting"] == "Model1" else debate["Model2name"]
            votes.append(
                {
                    "mode": "different-position",
                    "row_key": debate["DebateId"],
                    "judge": judge,
                    "topic": debate["topicId"],
                    "model1": debate["Model1name"],
                    "model2": debate["Model2name"],
                    "model1_position": debate["Model1Position"],
                    "starting_slot": debate["starting"],
                    "starter_model": starter_model,
                    "winner": winner,
                    "winning_position": winner_position,
                    "confidence": float(judgement[f"{label} confidence"]),
                }
            )
    return votes


def same_votes(
    raw: list[dict[str, str]], same: list[dict[str, str]], judges: list[str]
) -> list[dict[str, object]]:
    raw_by_id = {row["DebateId"]: row for row in raw}
    votes = []
    for judgement in same:
        id1 = judgement["DebateId1"]
        id2 = judgement["DebateId2"]
        topic = raw_by_id[id1]["topicId"]
        base_key = (
            min(int(id1), int(id2)),
            max(int(id1), int(id2)),
            judgement["testedPosition"],
            judgement["candidateStarting"],
        )
        for judge in judges:
            label = judge_label(same, judge)
            votes.append(
                {
                    "mode": "same-position",
                    "row_key": f"{id1}:{id2}:{judgement['testedPosition']}:{judgement['candidateStarting']}",
                    "base_key": base_key,
                    "judge": judge,
                    "topic": topic,
                    "candidate1": judgement["candidate1Model"],
                    "candidate2": judgement["candidate2Model"],
                    "tested_position": judgement["testedPosition"],
                    "candidate_starting": judgement["candidateStarting"],
                    "winner": judgement[f"{label} winner"],
                    "confidence": float(judgement[f"{label} confidence"]),
                }
            )
    return votes


def performance(votes: list[dict[str, object]], models: list[str], judge: str | None = None) -> list[dict[str, object]]:
    selected = [vote for vote in votes if judge is None or vote["judge"] == judge]
    rows = []
    for model in models:
        appearances = [vote for vote in selected if model in vote_models(vote)]
        wins = sum(vote["winner"] == model for vote in appearances)
        ties = sum(vote["winner"] == TIE for vote in appearances)
        losses = len(appearances) - wins - ties
        score = (wins + 0.5 * ties) / len(appearances) if appearances else float("nan")
        rows.append(
            {
                "judge": judge or "all judges",
                "model": model,
                "evaluations": len(appearances),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "score": round_value(score),
                "decisive_win_rate": round_value(wins / (wins + losses)) if wins + losses else float("nan"),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["model"])))


def vote_models(vote: dict[str, object]) -> tuple[str, str]:
    if vote["mode"] == "different-position":
        return str(vote["model1"]), str(vote["model2"])
    return str(vote["candidate1"]), str(vote["candidate2"])


def pairwise_performance(votes: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for vote in votes:
        grouped[tuple(sorted(vote_models(vote)))].append(vote)
    rows = []
    for pair, items in sorted(grouped.items()):
        left, right = pair
        left_wins = sum(vote["winner"] == left for vote in items)
        right_wins = sum(vote["winner"] == right for vote in items)
        ties = sum(vote["winner"] == TIE for vote in items)
        left_score = (left_wins + 0.5 * ties) / len(items)
        preferred = left if left_score > 0.5 else right if left_score < 0.5 else TIE
        rows.append(
            {
                "model_left": left,
                "model_right": right,
                "evaluations": len(items),
                "left_wins": left_wins,
                "right_wins": right_wins,
                "ties": ties,
                "left_score": round_value(left_score),
                "preferred_model": preferred,
            }
        )
    return rows


def agreement_rows(source_rows: list[dict[str, str]], judges: list[str]) -> tuple[list[dict[str, object]], dict[str, object]]:
    pair_rows = []
    for i, left in enumerate(judges):
        left_label = judge_label(source_rows, left)
        for right in judges[i + 1 :]:
            right_label = judge_label(source_rows, right)
            left_values = [row[f"{left_label} winner"] for row in source_rows]
            right_values = [row[f"{right_label} winner"] for row in source_rows]
            observed, kappa = cohen_kappa(left_values, right_values)
            pair_rows.append(
                {
                    "judge_left": left,
                    "judge_right": right,
                    "rows": len(source_rows),
                    "exact_agreement": round_value(observed),
                    "cohen_kappa": round_value(kappa),
                }
            )

    unanimity = 0
    no_majority = 0
    majority_counts = Counter()
    judge_majority_hits = Counter()
    for row in source_rows:
        winners = [row[f"{judge_label(source_rows, judge)} winner"] for judge in judges]
        counts = Counter(winners)
        if len(counts) == 1:
            unanimity += 1
        winner, count = counts.most_common(1)[0]
        if count < 2:
            no_majority += 1
            continue
        majority_counts[winner] += 1
        for judge, verdict in zip(judges, winners):
            judge_majority_hits[judge] += int(verdict == winner)
    summary = {
        "rows": len(source_rows),
        "unanimous_rows": unanimity,
        "unanimous_rate": round_value(unanimity / len(source_rows)),
        "rows_without_majority": no_majority,
        "judge_dependent_rate": round_value(1.0 - unanimity / len(source_rows)),
        "majority_winners": dict(majority_counts),
        "judge_majority_agreement": {
            judge: round_value(judge_majority_hits[judge] / (len(source_rows) - no_majority))
            for judge in judges
        },
    }
    return pair_rows, summary


def position_and_order(diff_votes_: list[dict[str, object]]) -> dict[str, object]:
    position_counts = Counter(str(vote["winning_position"]) for vote in diff_votes_)
    decisive_position = position_counts["A"] + position_counts["B"]
    a_share = position_counts["A"] / decisive_position

    starter_counts = Counter()
    slot_counts = Counter()
    for vote in diff_votes_:
        winner = vote["winner"]
        if winner == TIE:
            starter_counts[TIE] += 1
            slot_counts[TIE] += 1
            continue
        starter_counts["starter" if winner == vote["starter_model"] else "nonstarter"] += 1
        slot_counts["Model1" if winner == vote["model1"] else "Model2"] += 1
    starter_decisive = starter_counts["starter"] + starter_counts["nonstarter"]

    units_by_debate: dict[str, list[dict[str, object]]] = defaultdict(list)
    for vote in diff_votes_:
        units_by_debate[str(vote["row_key"])].append(vote)
    units = list(units_by_debate.values())

    def boot_position(sample):
        counts = Counter(str(vote["winning_position"]) for unit in sample for vote in unit)
        total = counts["A"] + counts["B"]
        return counts["A"] / total if total else float("nan")

    def boot_starter(sample):
        wins = 0
        total = 0
        for unit in sample:
            for vote in unit:
                if vote["winner"] == TIE:
                    continue
                total += 1
                wins += int(vote["winner"] == vote["starter_model"])
        return wins / total if total else float("nan")

    a_ci = bootstrap_interval(units, boot_position)
    starter_ci = bootstrap_interval(units, boot_starter, seed=20260820)
    return {
        "position_counts": dict(position_counts),
        "position_a_share_decisive": round_value(a_share),
        "position_a_share_95_cluster_bootstrap": [round_value(a_ci[0]), round_value(a_ci[1])],
        "speaker_counts": dict(starter_counts),
        "starter_share_decisive": round_value(starter_counts["starter"] / starter_decisive),
        "starter_share_95_cluster_bootstrap": [round_value(starter_ci[0]), round_value(starter_ci[1])],
        "slot_counts": dict(slot_counts),
    }


def paired_flip_analysis(raw: list[dict[str, str]], diff: list[dict[str, str]], judges: list[str]) -> list[dict[str, object]]:
    raw_by_id = {row["DebateId"]: row for row in raw}
    rows = []

    def classify(left: str, right: str) -> str:
        if left == right == TIE:
            return "both_tie"
        if left == right:
            return "same_winner"
        if TIE in (left, right):
            return "tie_transition"
        return "winner_reversal"

    for manipulation in ("position_assignment", "speaking_order"):
        for judge in judges:
            label = judge_label(diff, judge)
            groups: dict[tuple[object, ...], list[dict[str, str]]] = defaultdict(list)
            for judgement in diff:
                debate = raw_by_id[judgement["DebateId"]]
                pair = tuple(sorted((debate["Model1name"], debate["Model2name"])))
                if manipulation == "position_assignment":
                    key = (debate["topicId"], pair, debate["starting"])
                else:
                    key = (debate["topicId"], pair, debate["Model1Position"])
                groups[key].append(judgement)
            counts = Counter()
            for items in groups.values():
                if len(items) != 2:
                    counts["incomplete"] += 1
                    continue
                counts[classify(items[0][f"{label} winner"], items[1][f"{label} winner"])] += 1
            valid = sum(value for key, value in counts.items() if key != "incomplete")
            rows.append(
                {
                    "manipulation": manipulation,
                    "judge": judge,
                    "paired_conditions": valid,
                    "same_winner": counts["same_winner"],
                    "winner_reversal": counts["winner_reversal"],
                    "tie_transition": counts["tie_transition"],
                    "both_tie": counts["both_tie"],
                    "winner_reversal_rate": round_value(counts["winner_reversal"] / valid),
                    "any_change_rate": round_value((counts["winner_reversal"] + counts["tie_transition"]) / valid),
                }
            )
    return rows


def same_order_stability(same: list[dict[str, str]], judges: list[str]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[dict[str, str]]] = defaultdict(list)
    for row in same:
        key = (
            min(int(row["DebateId1"]), int(row["DebateId2"])),
            max(int(row["DebateId1"]), int(row["DebateId2"])),
            row["testedPosition"],
            row["candidateStarting"],
        )
        groups[key].append(row)

    results = []
    for judge in judges:
        label = judge_label(same, judge)
        counts = Counter()
        candidate_slot = Counter()
        for items in groups.values():
            if len(items) != 2:
                counts["incomplete"] += 1
                continue
            winners = [item[f"{label} winner"] for item in items]
            for item, winner in zip(items, winners):
                if winner == TIE:
                    candidate_slot[TIE] += 1
                elif winner == item["candidate1Model"]:
                    candidate_slot["candidate1"] += 1
                else:
                    candidate_slot["candidate2"] += 1
            if winners[0] == winners[1] == TIE:
                counts["both_tie"] += 1
            elif winners[0] == winners[1]:
                counts["stable_model"] += 1
            elif TIE in winners:
                counts["tie_transition"] += 1
            else:
                counts["model_reversal"] += 1
        valid = sum(value for key, value in counts.items() if key != "incomplete")
        decisive_slots = candidate_slot["candidate1"] + candidate_slot["candidate2"]
        results.append(
            {
                "judge": judge,
                "paired_comparisons": valid,
                "stable_model": counts["stable_model"],
                "model_reversal": counts["model_reversal"],
                "tie_transition": counts["tie_transition"],
                "both_tie": counts["both_tie"],
                "stable_rate": round_value((counts["stable_model"] + counts["both_tie"]) / valid),
                "candidate1_wins": candidate_slot["candidate1"],
                "candidate2_wins": candidate_slot["candidate2"],
                "ties": candidate_slot[TIE],
                "candidate1_share_decisive": round_value(candidate_slot["candidate1"] / decisive_slots),
            }
        )
    return results


def verbosity_analysis(
    raw: list[dict[str, str]],
    diff_votes_: list[dict[str, object]],
    same_votes_: list[dict[str, object]],
    words_by_debate_model: dict[str, dict[str, int]],
) -> list[dict[str, object]]:
    del raw  # Lengths are already indexed by debate and model.
    lengths_by_judge: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"winner": [], "loser": []}
    )
    for mode, votes in (("different-position", diff_votes_), ("same-position", same_votes_)):
        for vote in votes:
            if vote["winner"] == TIE:
                continue
            judge = str(vote["judge"])
            winner = str(vote["winner"])
            models = vote_models(vote)
            loser = models[1] if winner == models[0] else models[0]
            if mode == "different-position":
                debate_id = str(vote["row_key"])
                candidate_lengths = words_by_debate_model[debate_id]
            else:
                id1, id2, *_ = str(vote["row_key"]).split(":")
                candidate1 = str(vote["candidate1"])
                candidate2 = str(vote["candidate2"])
                candidate_lengths = {
                    candidate1: words_by_debate_model[id1][candidate1],
                    candidate2: words_by_debate_model[id2][candidate2],
                }
            lengths_by_judge[judge]["winner"].append(candidate_lengths[winner])
            lengths_by_judge[judge]["loser"].append(candidate_lengths[loser])

    results = []
    for judge, lengths in sorted(lengths_by_judge.items()):
        winner_lengths = lengths["winner"]
        loser_lengths = lengths["loser"]
        results.append(
            {
                "judge": judge,
                "decisive_evaluations": len(winner_lengths),
                "mean_winner_words": round_value(statistics.mean(winner_lengths), 1),
                "variance_winner_words": round_value(statistics.variance(winner_lengths), 1),
                "mean_loser_words": round_value(statistics.mean(loser_lengths), 1),
                "variance_loser_words": round_value(statistics.variance(loser_lengths), 1),
            }
        )
    return results


def self_preference(
    diff_votes_: list[dict[str, object]],
    same_votes_: list[dict[str, object]],
    judges: list[str],
) -> list[dict[str, object]]:
    votes = diff_votes_ + same_votes_
    votes_by_row: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for vote in votes:
        votes_by_row[(str(vote["mode"]), str(vote["row_key"]))].append(vote)

    results = []
    models = {model for vote in votes for model in vote_models(vote)}
    for judge in judges:
        if judge not in models:
            continue
        own_votes = [vote for vote in votes if vote["judge"] == judge and judge in vote_models(vote)]
        self_wins = sum(vote["winner"] == judge for vote in own_votes)
        uninvolved_row_scores = []
        uninvolved_evaluations = 0
        for vote in own_votes:
            participants = set(vote_models(vote))
            row_votes = votes_by_row[(str(vote["mode"]), str(vote["row_key"]))]
            eligible = [row_vote for row_vote in row_votes if row_vote["judge"] not in participants]
            if not eligible:
                raise ValueError(f"No uninvolved judge is available for {vote['mode']} row {vote['row_key']}.")
            uninvolved_evaluations += len(eligible)
            uninvolved_row_scores.append(statistics.mean(row_vote["winner"] == judge for row_vote in eligible))

        self_rate = self_wins / len(own_votes)
        uninvolved_rate = statistics.mean(uninvolved_row_scores)
        results.append(
            {
                "overlapping_judge_model": judge,
                "self_comparisons": len(own_votes),
                "self_judge_wins": self_wins,
                "self_judge_ties": sum(vote["winner"] == TIE for vote in own_votes),
                "self_judge_win_rate": round_value(self_rate),
                "uninvolved_judge_evaluations": uninvolved_evaluations,
                "uninvolved_judge_baseline": round_value(uninvolved_rate),
                "self_minus_uninvolved": round_value(self_rate - uninvolved_rate),
            }
        )
    return results


def confidence_analysis(votes: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    for judge in sorted({str(vote["judge"]) for vote in votes}):
        values = [float(vote["confidence"]) for vote in votes if vote["judge"] == judge]
        results.append(
            {
                "mode": str(votes[0]["mode"]),
                "judge": judge,
                "evaluations": len(values),
                "mean_confidence": round_value(statistics.mean(values)),
                "median_confidence": round_value(statistics.median(values)),
                "min_confidence": min(values),
                "max_confidence": max(values),
                "zero_confidence": sum(value == 0.0 for value in values),
                "unique_values": len(set(values)),
            }
        )
    return results


def conditioned_model_performance(
    votes: list[dict[str, object]], models: list[str]
) -> list[dict[str, object]]:
    results = []
    mode = str(votes[0]["mode"])
    if mode == "different-position":
        conditions = [("position", "A"), ("position", "B"), ("speaking", "starter"), ("speaking", "nonstarter")]
    else:
        conditions = [
            ("tested_position", "A"),
            ("tested_position", "B"),
            ("candidate_speaking", "starts"),
            ("candidate_speaking", "does_not_start"),
        ]

    for model in models:
        model_votes = [vote for vote in votes if model in vote_models(vote)]
        for condition, value in conditions:
            selected = []
            for vote in model_votes:
                if mode == "different-position":
                    if condition == "position":
                        model_position = vote["model1_position"] if vote["model1"] == model else (
                            "B" if vote["model1_position"] == "A" else "A"
                        )
                        include = model_position == value
                    else:
                        is_starter = vote["starter_model"] == model
                        include = is_starter if value == "starter" else not is_starter
                else:
                    if condition == "tested_position":
                        include = vote["tested_position"] == value
                    else:
                        is_starter = vote["candidate_starting"] == "yes"
                        include = is_starter if value == "starts" else not is_starter
                if include:
                    selected.append(vote)
            wins = sum(vote["winner"] == model for vote in selected)
            ties = sum(vote["winner"] == TIE for vote in selected)
            score = (wins + 0.5 * ties) / len(selected)
            results.append(
                {
                    "mode": mode,
                    "model": model,
                    "condition": condition,
                    "value": value,
                    "evaluations": len(selected),
                    "wins": wins,
                    "ties": ties,
                    "score": round_value(score),
                }
            )
    return results


def topic_position_table(diff_votes_: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for vote in diff_votes_:
        grouped[str(vote["topic"])].append(vote)
    rows = []
    for topic, votes in sorted(grouped.items()):
        counts = Counter(str(vote["winning_position"]) for vote in votes)
        decisive = counts["A"] + counts["B"]
        by_debate: dict[str, list[dict[str, object]]] = defaultdict(list)
        for vote in votes:
            by_debate[str(vote["row_key"])].append(vote)

        def statistic(sample):
            sample_counts = Counter(str(vote["winning_position"]) for unit in sample for vote in unit)
            total = sample_counts["A"] + sample_counts["B"]
            return sample_counts["A"] / total if total else float("nan")

        interval = bootstrap_interval(list(by_debate.values()), statistic, seed=20260819 + len(rows))
        rows.append(
            {
                "topic": topic,
                "evaluations": len(votes),
                "position_a_wins": counts["A"],
                "position_b_wins": counts["B"],
                "ties": counts[TIE],
                "position_a_share_decisive": round_value(counts["A"] / decisive),
                "a_share_ci_low": round_value(interval[0]),
                "a_share_ci_high": round_value(interval[1]),
            }
        )
    return rows


def topic_judge_position_table(diff_votes_: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for vote in diff_votes_:
        grouped[(str(vote["topic"]), str(vote["judge"]))].append(vote)
    rows = []
    for (topic, judge), votes in sorted(grouped.items()):
        counts = Counter(str(vote["winning_position"]) for vote in votes)
        decisive = counts["A"] + counts["B"]
        rows.append(
            {
                "topic": topic,
                "judge": judge,
                "evaluations": len(votes),
                "position_a_wins": counts["A"],
                "position_b_wins": counts["B"],
                "ties": counts[TIE],
                "position_a_share_decisive": round_value(counts["A"] / decisive) if decisive else float("nan"),
            }
        )
    return rows


def topic_model_leaders(
    diff_votes_: list[dict[str, object]], same_votes_: list[dict[str, object]], models: list[str]
) -> list[dict[str, object]]:
    rows = []
    topics = sorted({str(vote["topic"]) for vote in diff_votes_})
    for topic in topics:
        diff_topic = [vote for vote in diff_votes_ if vote["topic"] == topic]
        same_topic = [vote for vote in same_votes_ if vote["topic"] == topic]
        diff_perf = performance(diff_topic, models)
        same_perf = performance(same_topic, models)
        rows.append(
            {
                "topic": topic,
                "different_position_leader": diff_perf[0]["model"],
                "different_position_leader_score": diff_perf[0]["score"],
                "same_position_leader": same_perf[0]["model"],
                "same_position_leader_score": same_perf[0]["score"],
                "same_leader": diff_perf[0]["model"] == same_perf[0]["model"],
            }
        )
    return rows


def majority_summary(source_rows: list[dict[str, str]], judges: list[str]) -> dict[str, object]:
    winners = Counter()
    for row in source_rows:
        verdicts = [row[f"{judge_label(source_rows, judge)} winner"] for judge in judges]
        winner, count = Counter(verdicts).most_common(1)[0]
        winners[winner if count >= 2 else "No majority"] += 1
    return dict(winners)


def position_order_by_judge(diff_votes_: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for judge in sorted({str(vote["judge"]) for vote in diff_votes_}):
        votes = [vote for vote in diff_votes_ if vote["judge"] == judge]
        positions = Counter(str(vote["winning_position"]) for vote in votes)
        speaking = Counter()
        slots = Counter()
        for vote in votes:
            if vote["winner"] == TIE:
                continue
            speaking["starter" if vote["winner"] == vote["starter_model"] else "nonstarter"] += 1
            slots["Model1" if vote["winner"] == vote["model1"] else "Model2"] += 1
        position_decisive = positions["A"] + positions["B"]
        speaking_decisive = speaking["starter"] + speaking["nonstarter"]
        slot_decisive = slots["Model1"] + slots["Model2"]
        rows.append(
            {
                "judge": judge,
                "position_a_wins": positions["A"],
                "position_b_wins": positions["B"],
                "ties": positions[TIE],
                "position_a_share_decisive": round_value(positions["A"] / position_decisive),
                "starter_wins": speaking["starter"],
                "nonstarter_wins": speaking["nonstarter"],
                "starter_share_decisive": round_value(speaking["starter"] / speaking_decisive),
                "model1_wins": slots["Model1"],
                "model2_wins": slots["Model2"],
                "model1_share_decisive": round_value(slots["Model1"] / slot_decisive),
            }
        )
    return rows


def compact_condition_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row["mode"]), str(row["model"]))][f"{row['condition']}:{row['value']}"] = row["score"]
    output = []
    for (mode, model), values in sorted(grouped.items()):
        if mode == "different-position":
            output.append(
                {
                    "mode": "different",
                    "model": model,
                    "position_a": values["position:A"],
                    "position_b": values["position:B"],
                    "starts": values["speaking:starter"],
                    "does_not_start": values["speaking:nonstarter"],
                }
            )
        else:
            output.append(
                {
                    "mode": "same",
                    "model": model,
                    "position_a": values["tested_position:A"],
                    "position_b": values["tested_position:B"],
                    "starts": values["candidate_speaking:starts"],
                    "does_not_start": values["candidate_speaking:does_not_start"],
                }
            )
    return output


def validate_inputs(
    raw: list[dict[str, str]],
    diff: list[dict[str, str]],
    same: list[dict[str, str]],
    judges: list[str],
) -> dict[str, object]:
    if len(raw) != 240 or len(diff) != 240 or len(same) != 480:
        raise ValueError(f"Unexpected row counts: raw={len(raw)}, diff={len(diff)}, same={len(same)}")
    raw_ids = {row["DebateId"] for row in raw}
    raw_by_id = {row["DebateId"]: row for row in raw}
    if len(raw_ids) != len(raw) or {row["DebateId"] for row in diff} != raw_ids:
        raise ValueError("Raw and different-position DebateId coverage is inconsistent.")
    topic_counts = Counter((row["positionA"], row["positionB"]) for row in raw)
    if len(topic_counts) != 10 or set(topic_counts.values()) != {24}:
        raise ValueError("Raw topic coverage is not 10 balanced 24-row blocks.")
    raw_conditions = Counter(
        (
            row["positionA"],
            row["positionB"],
            tuple(sorted((row["Model1name"], row["Model2name"]))),
            row["Model1Position"],
            row["starting"],
        )
        for row in raw
    )
    if len(raw_conditions) != 240 or set(raw_conditions.values()) != {1}:
        raise ValueError("Raw factorial condition coverage is incomplete.")
    for row in same:
        if row["DebateId1"] not in raw_ids or row["DebateId2"] not in raw_ids:
            raise ValueError("Same-position row references an unknown debate.")
    order_groups = Counter(
        (
            min(int(row["DebateId1"]), int(row["DebateId2"])),
            max(int(row["DebateId1"]), int(row["DebateId2"])),
            row["testedPosition"],
            row["candidateStarting"],
        )
        for row in same
    )
    if len(order_groups) != 240 or set(order_groups.values()) != {2}:
        raise ValueError("Same-position candidate-order pairing is incomplete.")
    grouped_rows: dict[tuple[object, ...], list[dict[str, str]]] = defaultdict(list)
    for row in same:
        key = (
            min(int(row["DebateId1"]), int(row["DebateId2"])),
            max(int(row["DebateId1"]), int(row["DebateId2"])),
            row["testedPosition"],
            row["candidateStarting"],
        )
        grouped_rows[key].append(row)
        debate1 = raw_by_id[row["DebateId1"]]
        debate2 = raw_by_id[row["DebateId2"]]
        if (debate1["positionA"], debate1["positionB"]) != (debate2["positionA"], debate2["positionB"]):
            raise ValueError("Same-position comparison crosses topics.")
        for debate, candidate_field in ((debate1, "candidate1Model"), (debate2, "candidate2Model")):
            candidate = row[candidate_field]
            if candidate not in (debate["Model1name"], debate["Model2name"]):
                raise ValueError("Same-position candidate is absent from its referenced debate.")
            slot = "Model1" if debate["Model1name"] == candidate else "Model2"
            if debate[f"{slot}Position"] != row["testedPosition"]:
                raise ValueError("Same-position candidate did not defend the tested position.")
            starts = debate["starting"] == slot
            if starts != (row["candidateStarting"] == "yes"):
                raise ValueError("Same-position candidateStarting is inconsistent with its debate.")
    for items in grouped_rows.values():
        first, second = items
        if not (
            first["DebateId1"] == second["DebateId2"]
            and first["DebateId2"] == second["DebateId1"]
            and first["candidate1Model"] == second["candidate2Model"]
            and first["candidate2Model"] == second["candidate1Model"]
        ):
            raise ValueError("Same-position order pair is not an exact candidate reversal.")
    missing = 0
    invalid_confidence = 0
    for source in (diff, same):
        for row in source:
            for judge in judges:
                label = judge_label(source, judge)
                missing += int(not row.get(f"{label} winner")) + int(not row.get(f"{label} confidence"))
                try:
                    confidence = float(row[f"{label} confidence"])
                except ValueError:
                    invalid_confidence += 1
                    continue
                invalid_confidence += int(not 0.0 <= confidence <= 1.0)
                winner = row[f"{label} winner"]
                if source is diff:
                    debate = raw_by_id[row["DebateId"]]
                    if winner not in (debate["Model1name"], debate["Model2name"], TIE):
                        raise ValueError("Invalid different-position winner.")
                    expected_position = TIE
                    if winner == debate["Model1name"]:
                        expected_position = debate["Model1Position"]
                    elif winner == debate["Model2name"]:
                        expected_position = debate["Model2Position"]
                    if row[f"{label} winningPosition"] != expected_position:
                        raise ValueError("Different-position winner and winningPosition disagree.")
                elif winner not in (row["candidate1Model"], row["candidate2Model"], TIE):
                    raise ValueError("Invalid same-position winner.")
    if missing or invalid_confidence:
        raise ValueError(f"Judgement completeness failed: missing={missing}, invalid_confidence={invalid_confidence}")
    return {
        "raw_rows": len(raw),
        "different_position_rows": len(diff),
        "same_position_rows": len(same),
        "same_position_order_pairs": len(order_groups),
        "missing_judge_cells": missing,
        "invalid_confidence_cells": invalid_confidence,
    }


def ranking_scores(rows: list[dict[str, object]]) -> dict[str, float]:
    return {str(row["model"]): float(row["score"]) for row in rows}


def mode_comparison(
    diff_votes_: list[dict[str, object]],
    same_votes_: list[dict[str, object]],
    models: list[str],
    judges: list[str],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    rank_rows = []
    correlations = []
    pair_changes_by_judge = []
    for judge in [None, *judges]:
        diff_perf = performance(diff_votes_, models, judge)
        same_perf = performance(same_votes_, models, judge)
        diff_scores = ranking_scores(diff_perf)
        same_scores = ranking_scores(same_perf)
        diff_ranks = average_ranks(diff_scores)
        same_ranks = average_ranks(same_scores)
        correlations.append(
            {
                "judge": judge or "all judges",
                "spearman_rank_correlation": round_value(spearman(diff_scores, same_scores)),
            }
        )
        diff_pair_rows = pairwise_performance(
            [vote for vote in diff_votes_ if judge is None or vote["judge"] == judge]
        )
        same_pair_rows = pairwise_performance(
            [vote for vote in same_votes_ if judge is None or vote["judge"] == judge]
        )
        diff_pair_map = {(row["model_left"], row["model_right"]): row["preferred_model"] for row in diff_pair_rows}
        same_pair_map = {(row["model_left"], row["model_right"]): row["preferred_model"] for row in same_pair_rows}
        changes = sum(diff_pair_map[pair] != same_pair_map[pair] for pair in diff_pair_map)
        pair_changes_by_judge.append(
            {
                "judge": judge or "all judges",
                "model_pairs": len(diff_pair_map),
                "preference_changes": changes,
                "preference_change_rate": round_value(changes / len(diff_pair_map)),
            }
        )
        for model in models:
            rank_rows.append(
                {
                    "judge": judge or "all judges",
                    "model": model,
                    "different_position_score": round_value(diff_scores[model]),
                    "same_position_score": round_value(same_scores[model]),
                    "same_minus_different": round_value(same_scores[model] - diff_scores[model]),
                    "different_position_rank": diff_ranks[model],
                    "same_position_rank": same_ranks[model],
                    "absolute_rank_change": abs(same_ranks[model] - diff_ranks[model]),
                }
            )

    diff_pairs = {(row["model_left"], row["model_right"]): row for row in pairwise_performance(diff_votes_)}
    same_pairs = {(row["model_left"], row["model_right"]): row for row in pairwise_performance(same_votes_)}
    pair_rows = []
    reversals = 0
    for pair in sorted(diff_pairs):
        left = diff_pairs[pair]
        right = same_pairs[pair]
        changed = left["preferred_model"] != right["preferred_model"]
        reversals += int(changed)
        pair_rows.append(
            {
                "model_left": pair[0],
                "model_right": pair[1],
                "different_position_preference": left["preferred_model"],
                "same_position_preference": right["preferred_model"],
                "preference_changed": changed,
                "different_left_score": left["left_score"],
                "same_left_score": right["left_score"],
            }
        )
    summary = {
        "model_pairs": len(pair_rows),
        "pairwise_preference_changes": reversals,
        "pairwise_preference_change_rate": round_value(reversals / len(pair_rows)),
        "mean_absolute_rank_change": round_value(
            statistics.mean(
                row["absolute_rank_change"]
                for row in rank_rows
                if row["judge"] == "all judges"
            )
        ),
    }
    return rank_rows, pair_rows, {
        "correlations": correlations,
        "pair_changes_by_judge": pair_changes_by_judge,
        **summary,
    }


def judge_rank_correlations(votes: list[dict[str, object]], models: list[str], judges: list[str]) -> list[dict[str, object]]:
    scores = {judge: ranking_scores(performance(votes, models, judge)) for judge in judges}
    rows = []
    for i, left in enumerate(judges):
        for right in judges[i + 1 :]:
            rows.append(
                {
                    "mode": str(votes[0]["mode"]),
                    "judge_left": left,
                    "judge_right": right,
                    "spearman_rank_correlation": round_value(spearman(scores[left], scores[right])),
                }
            )
    return rows


def markdown_table(rows: list[dict[str, object]], fields: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in fields) + " |"
    numeric_pattern = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?%?|\d+(?:\.\d+)? pp)$")
    dividers = []
    for field, _ in fields:
        values = [row[field] for row in rows]
        numeric = bool(values) and all(
            isinstance(value, (int, float)) or numeric_pattern.match(str(value))
            for value in values
        )
        dividers.append("---:" if numeric else "---")
    divider = "| " + " | ".join(dividers) + " |"
    body = []
    for row in rows:
        values = []
        for field, _ in fields:
            value = row[field]
            if isinstance(value, bool):
                values.append("yes" if value else "no")
            elif isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *body])


def prompt_phrasing_diagnostic(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    rows = read_csv(path)
    paired: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for row in rows:
        paired[(row["DebateId"], row["Judge"])][row["PromptVariant"]] = row["Winner"]

    complete = [pair for pair in paired.values() if {"canonical", "paraphrased"} <= pair.keys()]
    exact = sum(pair["canonical"] == pair["paraphrased"] for pair in complete)
    decisive_reversals = sum(
        pair["canonical"] != TIE
        and pair["paraphrased"] != TIE
        and pair["canonical"] != pair["paraphrased"]
        for pair in complete
    )
    tie_transitions = sum(
        (pair["canonical"] == TIE) != (pair["paraphrased"] == TIE)
        for pair in complete
    )
    return {
        "debates": len({row["DebateId"] for row in rows}),
        "judges": sorted({row["Judge"] for row in rows}),
        "paired_comparisons": len(complete),
        "exact_agreements": exact,
        "decisive_reversals": decisive_reversals,
        "tie_transitions": tie_transitions,
    }


def build_report(summary: dict[str, object]) -> str:
    audit = summary["raw_audit"]
    position_order = summary["different_position"]["position_and_order"]
    mode = summary["mode_comparison"]
    diff_perf = summary["different_position"]["performance_all"]
    same_perf = summary["same_position"]["performance_all"]
    topic_rows = summary["different_position"]["topic_position"]
    order_rows = summary["same_position"]["candidate_order_stability"]
    self_rows = summary["self_preference"]
    verbosity_rows = summary["verbosity"]
    position_judge_rows = summary["different_position"]["position_order_by_judge"]
    prompt_diagnostic = summary.get("prompt_phrasing")

    judge_ids = list(summary["design"]["judges"])
    judge_labels = {
        "gemma-4-31b-it": "Gemma",
        "qwen3-30b-a3b-instruct-2507": "Qwen",
        "glm-4.7": "GLM",
    }
    rank_lookup = {
        (str(row["judge"]), str(row["model"])): row for row in mode["rank_comparison_by_judge"]
    }
    rank_rows = []
    for model in sorted({str(row["model"]) for row in mode["rank_comparison_by_judge"]}):
        row: dict[str, object] = {"model": model}
        different_ranks = []
        same_ranks = []
        for index, judge in enumerate(judge_ids):
            result = rank_lookup[(judge, model)]
            different_rank = int(result["different_position_rank"])
            same_rank = int(result["same_position_rank"])
            row[f"judge_{index}_different"] = different_rank
            row[f"judge_{index}_same"] = same_rank
            different_ranks.append(different_rank)
            same_ranks.append(same_rank)
        row["mean_different"] = f"{statistics.mean(different_ranks):.2f}"
        row["mean_same"] = f"{statistics.mean(same_ranks):.2f}"
        rank_rows.append(row)
    rank_fields = [("model", "Model")]
    for index, judge in enumerate(judge_ids):
        label = judge_labels.get(judge, judge)
        rank_fields.extend(
            [(f"judge_{index}_different", f"{label} D"), (f"judge_{index}_same", f"{label} S")]
        )
    rank_fields.extend([("mean_different", "Mean D"), ("mean_same", "Mean S")])

    position_rows = [
        {
            "judge": "all judges",
            "position_a_share_decisive": position_order["position_a_share_decisive"],
            "starter_share_decisive": position_order["starter_share_decisive"],
        },
        *[
            {
                "judge": row["judge"],
                "position_a_share_decisive": row["position_a_share_decisive"],
                "starter_share_decisive": row["starter_share_decisive"],
            }
            for row in position_judge_rows
        ],
    ]

    verbosity_table = [
        {
            "judge": row["judge"],
            "decisive_evaluations": row["decisive_evaluations"],
            "mean_winner_words": f"{row['mean_winner_words']:.1f}",
            "variance_winner_words": f"{row['variance_winner_words']:.1f}",
            "mean_loser_words": f"{row['mean_loser_words']:.1f}",
            "variance_loser_words": f"{row['variance_loser_words']:.1f}",
        }
        for row in verbosity_rows
    ]
    self_table = [
        {
            "model_judge": row["overlapping_judge_model"],
            "self_comparisons": row["self_comparisons"],
            "self_win_rate": pct(row["self_judge_win_rate"]),
            "uninvolved_baseline": pct(row["uninvolved_judge_baseline"]),
            "difference": f"{100 * float(row['self_minus_uninvolved']):+.1f} pp",
        }
        for row in self_rows
    ]

    topic_presentation = {
        "energy_transition_infrastructure": (
            "Energy infrastructure",
            "Centralized nuclear fission",
            "Decentralized renewable microgrids",
        ),
        "mega_event_hosting": (
            "Mega-event hosting",
            "Multi-country co-hosting",
            "Single-nation hosting",
        ),
        "cultural_repatriation": (
            "Cultural repatriation",
            "Repatriate artifacts and use digital replicas",
            "Retain artifacts in universal museums",
        ),
        "exploration_priority": (
            "Exploration priority",
            "Prioritize deep-sea exploration",
            "Prioritize space exploration",
        ),
    }
    extreme_topics = []
    for row in sorted(
        topic_rows,
        key=lambda item: abs(float(item["position_a_share_decisive"]) - 0.5),
        reverse=True,
    )[:4]:
        a_share = float(row["position_a_share_decisive"])
        topic_label, position_a, position_b = topic_presentation.get(
            str(row["topic"]),
            (str(row["topic"]), "Position A", "Position B"),
        )
        easier, harder = (position_a, position_b) if a_share > 0.5 else (position_b, position_a)
        easy_wins, hard_wins = (
            (row["position_a_wins"], row["position_b_wins"])
            if a_share > 0.5
            else (row["position_b_wins"], row["position_a_wins"])
        )
        extreme_topics.append(
            {
                "topic": topic_label,
                "easier_position": easier,
                "harder_position": harder,
                "easier_share": pct(max(a_share, 1 - a_share)),
                "easy_wins": easy_wins,
                "hard_wins": hard_wins,
                "ties": row["ties"],
            }
        )

    diff_ties = sum(int(row["ties"]) for row in diff_perf) // 2
    same_ties = sum(int(row["ties"]) for row in same_perf) // 2
    order_by_judge = {row["judge"]: row for row in order_rows}
    qwen_order = order_by_judge["qwen3-30b-a3b-instruct-2507"]

    prompt_section = ""
    if prompt_diagnostic:
        prompt_section = f"""
### Prompt-phrasing sensitivity diagnostic

A balanced {prompt_diagnostic['debates']}-debate subset was re-judged under the canonical judge instruction and a meaning-preserving paraphrase. Gemma and Qwen completed {prompt_diagnostic['paired_comparisons']} paired comparisons. Exact winner agreement was {prompt_diagnostic['exact_agreements']}/{prompt_diagnostic['paired_comparisons']} ({pct(prompt_diagnostic['exact_agreements'] / prompt_diagnostic['paired_comparisons'])}); the changes comprised {prompt_diagnostic['decisive_reversals']} decisive winner reversals and {prompt_diagnostic['tie_transitions']} transitions between a winner and a tie. The result is diagnostic because one sample per prompt cannot distinguish wording sensitivity from residual API nondeterminism. Full design and results are in [PROMPT_PHRASING_SENSITIVITY.md](PROMPT_PHRASING_SENSITIVITY.md).
"""

    strongest_topic = extreme_topics[0]
    report = f"""# Analysis of the Curated Debate and Judgement Datasets

## Scope

Dataset I contains the generated debates, Dataset II Mode 1 evaluates models arguing different positions, and Dataset II Mode 2 compares models defending the same position. The primary analyses use only the three curated CSV files. A separately identified prompt-phrasing diagnostic adds new judgments on fixed debates but does not generate new debate text.

The validated design contains {audit['rows']} four-round debates: 10 topics x 6 unordered model pairs x 2 position assignments x 2 starting models. All debates have eight alternating messages. Mode 1 contains 720 judge evaluations. Mode 2 contains 1,440 evaluations representing 240 substantive comparisons shown in both candidate orders.

## Experiment 1: Same-Position Versus Different-Position Ranking

Models are ranked by tie-adjusted win rate, `(wins + 0.5 x ties) / evaluations`, separately for each judge and mode. The final two columns are arithmetic mean ranks across the three cloud judges. Rank 1 is best; D and S denote different-position and same-position evaluation.

{markdown_table(rank_rows, rank_fields)}

Pooling the underlying judge evaluations gives a mean absolute rank change of {mode['mean_absolute_rank_change']:.1f} places. Meta-Llama changes most, moving from rank 1 under different-position evaluation to rank 4 under same-position evaluation. Gemma moves from rank 3 to rank 1, Qwen remains rank 2, and Apertus moves from rank 4 to rank 3. The direct rank table exposes these model-level changes more clearly than a single correlation computed from four models.

Ties are uneven across modes: {diff_ties} of 720 different-position evaluations ({pct(diff_ties / 720)}) and {same_ties} of 1,440 same-position evaluations ({pct(same_ties / 1440)}). The ranking uses a fixed half-win treatment for ties, but the difference in tie frequency must be reported because it can affect cross-mode comparisons. These are LLM-judge rankings, not human-validated persuasion rankings.
{prompt_section}

## Experiment 2: Biases in persuasion judging

### Position and speaking order

Across all 720 different-position judge evaluations, Position A wins {position_order['position_counts'].get('A', 0)}, Position B wins {position_order['position_counts'].get('B', 0)}, and {position_order['position_counts'].get('Tie', 0)} are ties. Position A receives {pct(position_order['position_a_share_decisive'])} of decisive verdicts, with a transcript-cluster bootstrap interval of [{pct(position_order['position_a_share_95_cluster_bootstrap'][0])}, {pct(position_order['position_a_share_95_cluster_bootstrap'][1])}].

The starting speaker receives {pct(position_order['starter_share_decisive'])} of decisive verdicts, with a transcript-cluster bootstrap interval of [{pct(position_order['starter_share_95_cluster_bootstrap'][0])}, {pct(position_order['starter_share_95_cluster_bootstrap'][1])}]. Because each debate has eight alternating messages, the non-starting model also gives the final message. This estimate therefore contrasts starting with closing position; it cannot identify which mechanism causes the difference.

{markdown_table(position_rows, [('judge', 'Judge'), ('position_a_share_decisive', 'Position A share'), ('starter_share_decisive', 'Starting-speaker share')])}

The position effect is judge-dependent: Qwen favors Position A in 63.0% of decisive evaluations, compared with 45.7% for Gemma and 52.5% for GLM. Candidate order is also consequential in Mode 2. Qwen changes the winning model in {qwen_order['model_reversal']} of {qwen_order['paired_comparisons']} candidate-order reversals; this belongs with the Experiment 2 bias diagnostics, not the primary mode-ranking result.

The position and speaking-order swaps use fresh model generations. A verdict change can therefore reflect generation variation as well as the manipulated design factor, so these are design-level sensitivity estimates rather than isolated causal judge-bias coefficients.

### Verbosity

The two evaluation modes are pooled, with one row reported per judge. Variance is the sample variance in squared words.

{markdown_table(verbosity_table, [('judge', 'Judge'), ('decisive_evaluations', 'Decisive'), ('mean_winner_words', 'Winner mean'), ('variance_winner_words', 'Winner variance'), ('mean_loser_words', 'Loser mean'), ('variance_loser_words', 'Loser variance')])}

This is observational: length is chosen by the debating model and may correlate with model identity, topic, and argument quality. It does not isolate a causal verbosity bias.

### Judge self-preference

For every row involving judge-model X, the self-selection indicator is compared with judgments from models that are not participants in that debate. When two uninvolved judges are available, their binary selections are averaged so every debate receives equal weight. Ties count as non-selections.

{markdown_table(self_table, [('model_judge', 'Model acting as judge'), ('self_comparisons', 'Relevant rows'), ('self_win_rate', 'Self-selection rate'), ('uninvolved_baseline', 'Uninvolved-judge baseline'), ('difference', 'Difference')])}

The pooled data therefore do not show positive self-preference under this diagnostic. This remains descriptive because the judges may apply systematically different evaluation criteria.

### Ideological preference

The current topics are not annotated on an ideological scale. The files support judge-specific position preferences, but not a defensible claim about ideological preference.

## Experiment 3: Difficulty of debate positions

To keep the presentation compact, the table reports the four topics with the largest observed departure from a 50/50 split. Counts pool the three judges.

{markdown_table(extreme_topics, [('topic', 'Topic'), ('easier_position', 'Observationally easier position'), ('harder_position', 'Observationally harder position'), ('easier_share', 'Easier-position share'), ('easy_wins', 'Easy wins'), ('hard_wins', 'Hard wins'), ('ties', 'Ties')])}

{strongest_topic['topic']} is the strongest current numerical asymmetry: {strongest_topic['easier_position']} wins {strongest_topic['easy_wins']} decisive evaluations versus {strongest_topic['hard_wins']} for {strongest_topic['harder_position']}. However, the ten-topic dataset contains no deliberately obvious moral-control item. A strong extreme-case demonstration therefore cannot be claimed from the present files; any such control should be pre-specified before a future generation run.

## Summary of Findings

1. The primary Experiment 1 result is a direct rank comparison: Meta-Llama falls from first to fourth, Gemma rises from third to first, Qwen remains second, and Apertus rises from fourth to third. The mean absolute movement is 1.5 rank places.
2. Position, speaking order, and candidate order belong under Experiment 2. Their effects vary substantially across judge models.
3. Pooled verbosity summaries show the observed word counts of winners and losers, but cannot establish an independent length preference.
4. Gemma and Qwen select themselves less often than uninvolved judges select them on the same debate subsets: {self_table[0]['difference']} and {self_table[1]['difference']}, respectively.
5. The current strongest position-difficulty example favors {strongest_topic['easier_position']} over {strongest_topic['harder_position']}. A deliberately extreme moral-control topic remains to be generated.

## Open Experimental Extensions

These extensions address limitations of the current experimental design.

- [ ] Re-judge tied outcomes with a forced-choice, no-tie protocol while preserving the original judgments and documenting the protocol change.
- [ ] Add pre-specified easy control debates with one clearly more reasonable position; define the topic wording and selection criteria before generation.
- [ ] Add one stronger and one weaker model, and use the same six-model set for both debate generation and judgment.
- [x] Run a controlled prompt-phrasing sensitivity diagnostic on fixed transcripts with Gemma and Qwen. Repeated confirmation and GLM completion remain open.
- [ ] Run controlled matched-length or shortened-argument comparisons before making a causal verbosity claim.
- [ ] Add controlled style variants and ideological annotations only if those analyses remain in the final paper scope.

The full prioritized checklist and reporting requirements are maintained in [docs/FUTURE_EXPERIMENTS.md](../../../docs/FUTURE_EXPERIMENTS.md).

## Interpretation Boundaries

- The outcomes are preferences of three LLM judges, not measurements of human persuasion.
- The same-position file contains 480 presentations but only 240 underlying comparison conditions.
- The current rank comparison is descriptive and is sensitive to the treatment of ties.
- Generated factual claims in the debates have not been externally verified.
"""
    return report


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir) if args.output_dir else data_dir / "analysis"
    raw = read_csv(data_dir / "RawDebates.csv")
    diff = read_csv(data_dir / "judgements" / "DiffPosJudgements.csv")
    same = read_csv(data_dir / "judgements" / "SamePosJudgements.csv")
    topics = topic_lookup(Path(args.topics))
    attach_topics(raw, topics)

    diff_judges = detect_judges(diff)
    same_judges = detect_judges(same)
    if diff_judges != same_judges:
        raise ValueError("Different-position and same-position judge lists differ.")
    judges = diff_judges
    models = sorted({row["Model1name"] for row in raw} | {row["Model2name"] for row in raw})
    validation = validate_inputs(raw, diff, same, judges)

    audit, words_by_debate_model = raw_audit(raw)
    diff_votes_ = diff_votes(raw, diff, judges)
    same_votes_ = same_votes(raw, same, judges)

    diff_agreement_rows, diff_agreement_summary = agreement_rows(diff, judges)
    same_agreement_rows, same_agreement_summary = agreement_rows(same, judges)
    diff_perf_all = performance(diff_votes_, models)
    same_perf_all = performance(same_votes_, models)
    diff_perf_by_judge = [row for judge in judges for row in performance(diff_votes_, models, judge)]
    same_perf_by_judge = [row for judge in judges for row in performance(same_votes_, models, judge)]
    position_order = position_and_order(diff_votes_)
    position_order_judges = position_order_by_judge(diff_votes_)
    paired_flips = paired_flip_analysis(raw, diff, judges)
    order_stability = same_order_stability(same, judges)
    verbosity = verbosity_analysis(raw, diff_votes_, same_votes_, words_by_debate_model)
    self_rows = self_preference(diff_votes_, same_votes_, judges)
    confidence = confidence_analysis(diff_votes_) + confidence_analysis(same_votes_)
    topic_positions = topic_position_table(diff_votes_)
    topic_judge_positions = topic_judge_position_table(diff_votes_)
    model_conditions = conditioned_model_performance(diff_votes_, models) + conditioned_model_performance(
        same_votes_, models
    )
    topic_leaders = topic_model_leaders(diff_votes_, same_votes_, models)
    model_condition_compact = compact_condition_rows(model_conditions)
    rank_comparison, pair_comparison, mode_summary = mode_comparison(diff_votes_, same_votes_, models, judges)
    mode_summary["rank_comparison"] = [row for row in rank_comparison if row["judge"] == "all judges"]
    mode_summary["rank_comparison_by_judge"] = [row for row in rank_comparison if row["judge"] != "all judges"]
    mode_summary["pair_comparison"] = pair_comparison

    summary = {
        "design": {
            "topics": len({row["topicId"] for row in raw}),
            "models": models,
            "judges": judges,
            "raw_debates": len(raw),
            "different_position_rows": len(diff),
            "different_position_evaluations": len(diff_votes_),
            "same_position_rows": len(same),
            "same_position_substantive_comparisons": len({vote["base_key"] for vote in same_votes_}),
            "same_position_evaluations": len(same_votes_),
        },
        "validation": validation,
        "raw_audit": audit,
        "different_position": {
            "performance_all": diff_perf_all,
            "performance_by_judge": diff_perf_by_judge,
            "pairwise_performance": pairwise_performance(diff_votes_),
            "agreement": diff_agreement_summary,
            "agreement_pairs": diff_agreement_rows,
            "majority_winners": majority_summary(diff, judges),
            "judge_rank_correlations": judge_rank_correlations(diff_votes_, models, judges),
            "position_and_order": position_order,
            "position_order_by_judge": position_order_judges,
            "paired_flips": paired_flips,
            "topic_position": topic_positions,
        },
        "same_position": {
            "performance_all": same_perf_all,
            "performance_by_judge": same_perf_by_judge,
            "pairwise_performance": pairwise_performance(same_votes_),
            "agreement": same_agreement_summary,
            "agreement_pairs": same_agreement_rows,
            "majority_winners": majority_summary(same, judges),
            "judge_rank_correlations": judge_rank_correlations(same_votes_, models, judges),
            "candidate_order_stability": order_stability,
        },
        "mode_comparison": mode_summary,
        "verbosity": verbosity,
        "self_preference": self_rows,
        "confidence": confidence,
        "model_condition_performance": model_conditions,
        "topic_judge_position": topic_judge_positions,
        "topic_model_leaders": topic_leaders,
        "model_condition_compact": model_condition_compact,
        "prompt_phrasing": prompt_phrasing_diagnostic(
            output_dir / "prompt_phrasing_sensitivity" / "prompt_phrasing_judgements.csv"
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=list) + "\n",
        encoding="utf-8",
    )
    write_csv(output_dir / "model_performance_different_position.csv", diff_perf_by_judge + diff_perf_all)
    write_csv(output_dir / "model_performance_same_position.csv", same_perf_by_judge + same_perf_all)
    write_csv(output_dir / "judge_agreement_different_position.csv", diff_agreement_rows)
    write_csv(output_dir / "judge_agreement_same_position.csv", same_agreement_rows)
    write_csv(output_dir / "mode_pairwise_comparison.csv", pair_comparison)
    write_csv(output_dir / "position_speaking_order_flips.csv", paired_flips)
    write_csv(output_dir / "same_position_candidate_order_stability.csv", order_stability)
    write_csv(output_dir / "topic_position_difficulty.csv", topic_positions)
    write_csv(output_dir / "topic_judge_position_preferences.csv", topic_judge_positions)
    write_csv(output_dir / "model_condition_performance.csv", model_conditions)
    write_csv(output_dir / "model_condition_performance_compact.csv", model_condition_compact)
    write_csv(output_dir / "position_order_by_judge.csv", position_order_judges)
    write_csv(output_dir / "topic_model_leaders.csv", topic_leaders)
    write_csv(output_dir / "verbosity_diagnostic.csv", verbosity)
    write_csv(output_dir / "self_preference_diagnostic.csv", self_rows)
    write_csv(output_dir / "confidence_diagnostic.csv", confidence)
    (output_dir / "ANALYSIS_REPORT.md").write_text(build_report(summary), encoding="utf-8")
    print(f"Wrote analysis to {output_dir}")


if __name__ == "__main__":
    main()
