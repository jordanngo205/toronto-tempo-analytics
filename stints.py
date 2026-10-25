"""Rebuild who was on the court for Toronto from the play-by-play, then measure how each player's
production changes the longer she stays on the floor (her "stint").

A stint starts when a player checks in and ends when she checks out. The short breaks after Q1 and Q3
don't end a stint (players often stay on through them), but halftime and overtime do.
For every Tempo play we know which minute of her stint each player was in, so we can add up
Hollinger Game Score and plus-minus by "minutes into the stint".
"""
from collections import defaultdict

import numpy as np
import pandas as pd

from common import load
from flow import TOR, tempo_pbp

BINS = [0, 2, 4, 6, 8, 10, 12, 99]  # minutes into the stint
BIN_LABELS = ["0–2", "2–4", "4–6", "6–8", "8–10", "10–12", "12+"]


def bin_of(minutes):
    # which bin a "minutes into the stint" number falls in
    return int(np.searchsorted(BINS, minutes, side="right") - 1)


def period_bounds(per):
    # start and end of a period in seconds since tip-off (quarters 600 s, overtime 300 s)
    return ((per - 1) * 600, per * 600) if per <= 4 else (2400 + (per - 5) * 300, 2400 + (per - 4) * 300)


def credits(r, tempo_ids):
    """Game Score pieces from one play, as a list of (player id, points of Game Score)."""
    out = []
    a1 = r.athlete_id_1 if r.athlete_id_1 in tempo_ids else None
    a2 = r.athlete_id_2 if r.athlete_id_2 in tempo_ids else None
    txt, kind = str(r.text), str(r.type_text)
    made = bool(r.scoring_play)
    if bool(r.shooting_play):
        if "Free Throw" in kind:
            # free throws: +1 for a make, -0.4 for a miss
            if a1: out.append((a1, 1.0 if made else -0.4))
        else:
            # field goals: points + 0.4 for a make, -0.7 for every attempt
            if a1: out.append((a1, (int(r.score_value) + 0.4 if made else 0) - 0.7))
            if a2 and made: out.append((a2, 0.7))                           # assist
            if a2 and not made and "blocks" in txt: out.append((a2, 0.7))   # block
    elif "Offensive Rebound" in kind:
        if a1: out.append((a1, 0.7))
    elif "Defensive Rebound" in kind:
        if a1: out.append((a1, 0.3))
    elif "Turnover" in kind or kind in ("Traveling", "Kicked Ball"):
        if a1: out.append((a1, -1.0))
        if a2 and "steal" in txt: out.append((a2, 1.0))                     # steal
    elif "Foul" in kind and "Technical" not in kind:
        if a1: out.append((a1, -0.4))
    return out


def build(season=2026):
    p = tempo_pbp(season)
    for c in ["athlete_id_1", "athlete_id_2"]:
        p[c] = pd.to_numeric(p[c], errors="coerce").fillna(0).astype(int)
    pb = load("player_box", season)
    pb = pb[pb.team_id == TOR].copy()
    pb["athlete_id"] = pd.to_numeric(pb.athlete_id, errors="coerce").fillna(0).astype(int)
    tempo_ids = set(pb.athlete_id)
    names = pb.drop_duplicates("athlete_id").set_index("athlete_id").athlete_display_name.to_dict()
    starters = pb[pb.starter.astype(str) == "True"].groupby("game_id").athlete_id.apply(list).to_dict()

    gs = defaultdict(lambda: np.zeros(len(BIN_LABELS)))     # Game Score by player and bin
    pm = defaultdict(lambda: np.zeros(len(BIN_LABELS)))     # plus-minus by player and bin
    mins = defaultdict(lambda: np.zeros(len(BIN_LABELS)))   # minutes played by player and bin
    lengths = defaultdict(list)                             # every stint length (minutes) per player
    misses, matched = 0, 0  # Game Score pieces we could / couldn't place on a player who was on the floor

    def close(pid, start, end):
        # a stint ended: record its length and spread its minutes over the bins
        L = (end - start) / 60
        if L <= 0:
            return
        lengths[pid].append(L)
        for i in range(len(BIN_LABELS)):
            mins[pid][i] += max(0.0, min(L, BINS[i + 1]) - BINS[i])

    for gid, g in p.groupby("game_id", sort=False):
        g = g.sort_values("game_play_number")
        prev_on, prev_t1, prev_end_lineup = {}, 0, []
        for per, q in g.groupby("per"):
            t0, t1 = period_bounds(per)
            # who started the period: in Q1 the box-score starters, later the players whose first
            # appearance in the period isn't checking in
            if per == 1:
                lineup = list(starters.get(gid, []))[:5]
            else:
                first = {}
                for r in q.itertuples():
                    if r.type_text == "Substitution" and r.team_id == TOR:
                        first.setdefault(r.athlete_id_1, "in"); first.setdefault(r.athlete_id_2, "out")
                    else:
                        for a in (r.athlete_id_1, r.athlete_id_2):
                            if a in tempo_ids: first.setdefault(a, "event")
                lineup = [a for a, how in first.items() if how in ("out", "event") and a in tempo_ids][:5]
                # anyone who played the whole period without touching the ball: carry over from last period
                for a in prev_end_lineup:
                    if len(lineup) < 5 and a not in lineup and first.get(a) != "in":
                        lineup.append(a)
            # players still on from last quarter keep their stint going, except across halftime / into OT
            carry = per in (2, 4)
            for a, st in prev_on.items():
                if not (carry and a in lineup):
                    close(a, st, prev_t1)
            on = {a: (prev_on[a] if carry and a in prev_on else t0) for a in lineup}  # player id -> stint start time
            for r in q.itertuples():
                t = float(r.t)
                if r.type_text == "Substitution" and r.team_id == TOR:
                    if r.athlete_id_2 in on:
                        close(r.athlete_id_2, on.pop(r.athlete_id_2), t)
                    on[r.athlete_id_1] = t
                    continue
                # Game Score pieces go to the player at her current stint minute
                for pid, v in credits(r, tempo_ids):
                    if pid in on:
                        gs[pid][bin_of((t - on[pid]) / 60)] += v
                        matched += 1
                    else:
                        misses += 1
                # plus-minus: every Tempo player on the floor shares the scoring play
                if bool(r.scoring_play) and int(r.score_value) > 0:
                    sign = 1 if r.team_id == TOR else -1
                    for pid, st in on.items():
                        pm[pid][bin_of((t - st) / 60)] += sign * int(r.score_value)
            prev_end_lineup, prev_on, prev_t1 = list(on), dict(on), t1
        # end of the game: close whatever is still open
        for pid, st in prev_on.items():
            close(pid, st, prev_t1)

    # turn totals into per-40-minute rates (only bins with enough minutes to mean something)
    def per40(tot, m):
        return [round(40 * a / b, 1) if b >= 25 else None for a, b in zip(tot, m)]

    team_gs = sum(gs.values()); team_pm = sum(pm.values()); team_min = sum(mins.values())
    players = []
    for pid in sorted(mins, key=lambda k: -mins[k].sum()):
        if mins[pid].sum() < 300:
            continue
        L = np.array(lengths[pid])
        players.append({"name": names.get(pid, str(pid)), "min": round(float(mins[pid].sum())),
                        "avg_stint": round(float(L.mean()), 1), "long_share": round(float((L >= 8).mean()), 3),
                        "gs40": per40(gs[pid], mins[pid]), "pm40": per40(pm[pid], mins[pid]),
                        "mins": [round(float(x)) for x in mins[pid]]})
    return {"bins": BIN_LABELS, "team": {"gs40": per40(team_gs, team_min), "pm40": per40(team_pm, team_min),
                                         "mins": [round(float(x)) for x in team_min]},
            "players": players, "check": {"unmatched_credits": misses, "matched_credits": matched,
                                          "total_minutes": round(float(team_min.sum()))}}


if __name__ == "__main__":
    d = build()
    print(d["team"], d["check"])
    for p_ in d["players"]:
        print(p_["name"], p_["avg_stint"], p_["gs40"], p_["pm40"])
