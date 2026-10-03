"""Hand-count helper for the worked example in docs/domain/metric-dictionary.md.

Documentation tooling only (pickleball-domain-coach), not product code and not the analytics
implementation. It replays an invented Quick Tag sequence under the PROVISIONAL-UNVERIFIED side-out
doubles assumptions (start "0-0-2", side A serving) and prints the counts behind AN-01..AN-07.

Run: python3 docs/domain/tools/metric_example.py
"""

from __future__ import annotations

# (winning side, ending, fault subtype, responsible player)
RALLIES: list[tuple[str, str, str | None, str | None]] = [
    ("A", "winner", None, "A1"),
    ("B", "fault", "serve", "A2"),
    ("B", "winner", None, None),
    ("B", "unforced_error", None, "A1"),
    ("A", "forced_error", None, "B2"),
    ("A", "fault", "nvz", "B1"),
    ("A", "winner", None, "A2"),
    ("A", "replay", None, None),
    ("A", "unforced_error", None, None),
    ("B", "unforced_error", None, "A2"),
    ("A", "fault", None, None),
    ("B", "fault", "serve", "A1"),
    ("B", "winner", None, "B1"),
    ("B", "winner", None, "B2"),
]


def other(side: str) -> str:
    return "B" if side == "A" else "A"


def new_stats() -> dict:
    return {
        "served": 0,
        "served_won": 0,
        "recv": 0,
        "recv_won": 0,
        "turns": 0,
        "turn_points": 0,
        "serve_faults": 0,
        "untagged_serving_fault_subtype": 0,
        "ue": 0,
        "ue_by": {},
        "end": {"winner": 0, "unforced_error": 0, "forced_error": 0, "fault": 0},
    }


def main() -> None:
    server, number = "A", 2
    score = {"A": 0, "B": 0}
    stats = {"A": new_stats(), "B": new_stats()}
    stats["A"]["turns"] = 1
    runs: list[tuple[str, int]] = []
    run_side: str | None = None
    run_len = 0

    for i, (winner, ending, subtype, player) in enumerate(RALLIES, start=1):
        before = f"{score[server]}-{score[other(server)]}-{number} {server}"
        if ending == "replay":
            print(i, before, winner, ending, "excluded")
            continue
        s, r = stats[server], stats[other(server)]
        s["served"] += 1
        r["recv"] += 1
        actor = winner if ending == "winner" else other(winner)
        stats[actor]["end"][ending] += 1
        if ending == "unforced_error":
            stats[actor]["ue"] += 1
            key = player or "untagged"
            stats[actor]["ue_by"][key] = stats[actor]["ue_by"].get(key, 0) + 1
        if ending == "fault" and actor == server:
            if subtype == "serve":
                s["serve_faults"] += 1
            elif subtype is None:
                s["untagged_serving_fault_subtype"] += 1
        if winner == server:
            s["served_won"] += 1
            s["turn_points"] += 1
            score[server] += 1
            if run_side == server:
                run_len += 1
            else:
                if run_side:
                    runs.append((run_side, run_len))
                run_side, run_len = server, 1
        else:
            r["recv_won"] += 1
            if number == 1:
                number = 2
            else:
                server, number = other(server), 1
                stats[server]["turns"] += 1
        after = f"{score[server]}-{score[other(server)]}-{number} {server}"
        print(i, before, winner, ending, after)

    if run_side:
        runs.append((run_side, run_len))
    print("final score", score, "runs", runs)
    for side in "AB":
        print(side, stats[side])


if __name__ == "__main__":
    main()
