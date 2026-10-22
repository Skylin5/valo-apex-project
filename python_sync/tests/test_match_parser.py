"""Tests du parsing de match v4 (lancer depuis python_sync : python -m unittest discover -s tests)."""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.match_parser import (  # noqa: E402
    build_match_row,
    compute_round_stats,
    extract_weapon_kills,
    match_context,
    parse_started_at,
    rank_label,
)
from services.mmr_parser import mmr_rows  # noqa: E402


def who(puuid, team):
    return {"puuid": puuid, "name": puuid.upper(), "tag": "EUW", "team": team}


def kill(rnd, t, killer, victim, killer_team, victim_team, weapon="Vandal", assistants=()):
    return {
        "round": rnd, "time_in_round_in_ms": t,
        "killer": who(killer, killer_team), "victim": who(victim, victim_team),
        "assistants": [who(a, killer_team) for a in assistants],
        "weapon": {"id": "w", "name": weapon, "type": "Rifle"},
    }


def player(puuid, team, kills=0, deaths=0, tier=7):
    return {
        "puuid": puuid, "name": puuid.upper(), "tag": "EUW", "team_id": team,
        "agent": {"id": "a", "name": "Jett"}, "tier": {"id": tier, "name": "Bronze 2"},
        "account_level": 46,
        "stats": {"score": 4000, "kills": kills, "deaths": deaths, "assists": 4,
                  "headshots": 10, "bodyshots": 30, "legshots": 10,
                  "damage": {"dealt": 3000, "received": 2000}},
    }


# Équipes A (a1, a2) et B (b1, b2). 3 rounds : A gagne les rounds 0 et 2, B gagne le round 1.
MATCH = {
    "metadata": {
        "match_id": "m1", "map": {"id": "x", "name": "Ascent"},
        "queue": {"id": "competitive", "name": "Competitive", "mode_type": "Standard"},
        "season": {"id": "s", "short": "e10a5"}, "started_at": "2026-07-10T12:34:56Z",
    },
    "teams": [
        {"team_id": "A", "won": True, "rounds": {"won": 2, "lost": 1}},
        {"team_id": "B", "won": False, "rounds": {"won": 1, "lost": 2}},
    ],
    "players": [player("a1", "A", 4, 1), player("a2", "A", 1, 2), player("b1", "B", 1, 2), player("b2", "B", 1, 1)],
    "rounds": [
        {"id": 0, "winning_team": "A", "result": "Elimination", "ceremony": "", "stats": []},
        {"id": 1, "winning_team": "B", "result": "Elimination", "ceremony": "", "stats": []},
        {"id": 2, "winning_team": "A", "result": "Elimination", "ceremony": "", "stats": []},
    ],
    "kills": [
        # Round 0 : a1 fait un ace sans mort (flawless), a2 aide sur le 1er kill
        kill(0, 1000, "a1", "b1", "A", "B", assistants=["a2"]),
        kill(0, 2000, "a1", "b2", "A", "B"),
        # Round 1 : b1 tue a1, a2 venge a1 en 3 s (a1 tradé), puis b2 tue a2
        kill(1, 1000, "b1", "a1", "B", "A", weapon="Sheriff"),
        kill(1, 4000, "a2", "b1", "A", "B"),
        kill(1, 20000, "b2", "a2", "B", "A"),
        # Round 2 : a1 tue b1, b2 tue a1 (b1 tradé), a2 tue b2 8 s plus tard (trop tard pour a1)
        kill(2, 1000, "a1", "b1", "A", "B"),
        kill(2, 5000, "b2", "a1", "B", "A"),
        kill(2, 13000, "a2", "b2", "A", "B"),
        # Kill sans arme (capacité) : ignoré pour les armes
        {**kill(2, 14000, "a1", "b2", "A", "B"), "weapon": {"id": None, "name": None, "type": None}},
    ],
}


class ContextTest(unittest.TestCase):
    def test_context_values(self):
        ctx = match_context(MATCH)
        self.assertEqual(ctx["carte"], "Ascent")
        self.assertEqual(ctx["mode_jeu"], "Competitive")
        self.assertEqual(ctx["nb_rounds"], 3)
        self.assertEqual(ctx["saison"], "e10a5")
        self.assertEqual(ctx["date_match"], datetime(2026, 7, 10, 12, 34, 56))

    def test_started_at_invalid_or_missing(self):
        self.assertIsNone(parse_started_at(None))
        self.assertIsNone(parse_started_at("pas une date"))

    def test_rank_label_mapping(self):
        self.assertEqual(rank_label(None), "1 - Débutant (Niv 1-20)")
        self.assertEqual(rank_label(0), "1 - Débutant (Niv 1-20)")
        self.assertEqual(rank_label(4), "2 - Fer")
        self.assertEqual(rank_label(7), "3 - Bronze")
        self.assertEqual(rank_label(10), "4 - Argent")
        self.assertEqual(rank_label(13), "5 - Or")
        self.assertEqual(rank_label(15), "6 - Platine")
        self.assertEqual(rank_label(27), "6 - Platine")


class WeaponKillsTest(unittest.TestCase):
    def test_kills_per_player_and_weapon(self):
        kills = extract_weapon_kills(MATCH)
        self.assertEqual(dict(kills["a1#euw"]), {"Vandal": 3})
        self.assertEqual(dict(kills["b1#euw"]), {"Sheriff": 1})

    def test_kills_without_weapon_are_ignored(self):
        kills = extract_weapon_kills(MATCH)
        self.assertEqual(sum(kills["a1#euw"].values()), 3)  # le kill sans arme n'est pas compté


class RoundStatsTest(unittest.TestCase):
    def setUp(self):
        self.stats = compute_round_stats(MATCH)

    def test_first_bloods(self):
        self.assertEqual(self.stats["a1"]["first_bloods"], 2)  # rounds 0 et 2
        self.assertEqual(self.stats["b1"]["first_bloods"], 1)  # round 1

    def test_flawless_only_for_winning_team_without_death(self):
        # Round 0 : A gagne sans mort. Round 2 : A gagne mais a1 est mort -> pas flawless.
        self.assertEqual(self.stats["a1"]["flawless_rounds"], 1)
        self.assertEqual(self.stats["a2"]["flawless_rounds"], 1)
        self.assertEqual(self.stats["b1"]["flawless_rounds"], 0)

    def test_ace(self):
        match = {**MATCH, "kills": [
            kill(0, 1000 * i, "a1", f"b{i}", "A", "B") for i in range(1, 6)
        ]}
        self.assertEqual(compute_round_stats(match)["a1"]["aces"], 1)
        self.assertEqual(self.stats["a1"]["aces"], 0)

    def test_kast(self):
        # a1 : R0 kill, R1 mort mais tradé par a2 à +3 s, R2 kill -> 3/3
        self.assertEqual(self.stats["a1"]["kast_rounds"], 3)
        # a2 : R0 assist, R1 kill, R2 survit -> 3/3
        self.assertEqual(self.stats["a2"]["kast_rounds"], 3)
        # b1 : R0 mort non tradé (b2 ne venge pas), R1 kill, R2 mort mais tradé (b2 tue a1 4 s après) -> 2/3
        self.assertEqual(self.stats["b1"]["kast_rounds"], 2)

    def test_death_traded_too_late_does_not_count(self):
        # b2 tue a1 à 5 s ; a2 venge a1 à 13 s (8 s > 5 s) : a1 n'est pas tradé au round 2,
        # mais a1 a fait un kill ce round-là, donc on isole le cas sans kill ni assist.
        match = {**MATCH, "rounds": [MATCH["rounds"][2]], "kills": [
            kill(2, 5000, "b2", "a1", "B", "A"),
            kill(2, 13000, "a2", "b2", "A", "B"),
        ]}
        self.assertEqual(compute_round_stats(match)["a1"]["kast_rounds"], 0)
        match["kills"][1]["time_in_round_in_ms"] = 8000  # 3 s après : tradé
        self.assertEqual(compute_round_stats(match)["a1"]["kast_rounds"], 1)


class BuildRowTest(unittest.TestCase):
    def test_row_values(self):
        ctx = match_context(MATCH)
        row = build_match_row(ctx, MATCH["players"][0], compute_round_stats(MATCH))
        self.assertEqual(row["r_id"], "A1#EUW")
        self.assertEqual(row["won"], 1)
        self.assertEqual((row["s_eq"], row["s_en"]), (2, 1))
        self.assertEqual(row["adr"], 1000.0)  # 3000 dégâts / 3 rounds
        self.assertEqual((row["hp"], row["bp"], row["lp"]), (20.0, 60.0, 20.0))
        self.assertEqual(row["role"], "Duelist")
        self.assertEqual(row["rang"], "3 - Bronze")
        self.assertEqual((row["fb"], row["aces"], row["flawless"]), (2, 0, 1))
        self.assertEqual(row["kast"], 100.0)
        self.assertEqual(row["saison"], "e10a5")


class MmrRowsTest(unittest.TestCase):
    def test_rows_are_built_and_entries_without_match_skipped(self):
        history = [
            {"match_id": "m1", "date": "2026-07-10T12:00:00Z", "map": {"name": "Ascent"},
             "season": {"short": "e10a5"}, "tier": {"id": 7, "name": "Bronze 2"},
             "elo": 700, "rr": 50, "last_change": 18},
            {"date": "2026-07-09T12:00:00Z"},
        ]
        rows = mmr_rows("Nova#roma", history)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["elo"], rows[0]["variation"], rows[0]["tier_nom"]), (700, 18, "Bronze 2"))


if __name__ == "__main__":
    unittest.main()
