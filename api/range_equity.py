import csv
import os
import random

from .equity import monte_carlo_equity  # adjust import to your project
from .hand_constants import ALL_169_HANDS
from .range_parser import parse_range, expand_range
from typing import List, Tuple

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
RANKS = "23456789TJQKA"
SUITS = "cdhs"

import csv
import os

#----------------------------------------------
# CACHING
#----------------------------------------------

def load_cache(filename):
    if not os.path.exists(filename):
        return {}

    cache = {}
    with open(filename, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty or malformed rows
            if not row or "hand" not in row or row["hand"] is None:
                continue

            try:
                hand = row["hand"].strip()
                cache[hand] = (
                    float(row["hero_win"]),
                    float(row["villain_win"]),
                    float(row["tie"]),
                    int(float(row["total_simulation"])),
                )
            except Exception:
                # Skip corrupted rows
                continue

    return cache


def merge_results(cache, new_results):
    for hand, (hw, vw, t, ts) in new_results.items():
        if hand in cache:
            old_hw, old_vw, old_t, old_ts = cache[hand]
            cache[hand] = (
                ((old_hw * old_ts) + (hw * ts)) / (old_ts + ts),
                ((old_vw * old_ts) + (vw * ts)) / (old_ts + ts),
                ((old_t * old_ts) + (t * ts)) / (old_ts + ts),
                old_ts + ts,
            )
        else:
            cache[hand] = (hw, vw, t, ts)

def save_cache(filename, cache):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hand", "hero_win", "villain_win", "tie", "total_simulation"])

        for hand, (hw, vw, t, ts) in cache.items():
            writer.writerow([hand, hw, vw, t, ts])

#----------------------------------------------
# PARSING
#----------------------------------------------
#Parses through blocked cards
def card_from_str(card: str) -> Tuple[str, str]:
    # "As" -> ("A", "s")
    return card[0], card[1]

#Parses "AsAc" -> "AA"
def hand_class_from_str(hand_str):
    c1 = hand_str[:2]
    c2 = hand_str[2:]

    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]

    # order ranks high → low
    if RANKS.index(r1) < RANKS.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1

    if r1 == r2:
        return r1 + r2          # AA, KK, 77
    elif s1 == s2:
        return r1 + r2 + "s"    # AKs, QTs
    else:
        return r1 + r2 + "o"    # AKo, QTo

def combo_to_range_token(combo: str) -> str:
    c1, c2 = combo[:2], combo[2:]
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]

    if r1 == r2:
        return r1 + r2  # pair

    if s1 == s2:
        return r1 + r2 + "s"

    return r1 + r2 + "o"

#----------------------------------------------
# ACTUAL FUNCTIONS
#----------------------------------------------

def all_2card_combos():
    combos = []
    for r1 in RANKS:
        for s1 in SUITS:
            c1 = r1 + s1
            for r2 in RANKS:
                for s2 in SUITS:
                    c2 = r2 + s2
                    if c1 == c2:
                        continue
                    combos.append(c1 + c2)
    return combos

def blocked_by_board_or_hero(combo: str, used_cards: List[str]) -> bool:
    # combo: "AsKs" (4 chars)
    c1 = combo[:2]
    c2 = combo[2:]
    return c1 in used_cards or c2 in used_cards

def filter_blocked(combos: List[str], used_cards: List[str]) -> List[str]:
    return [c for c in combos if not blocked_by_board_or_hero(c, used_cards)]

def random_villain_combo():
    RANKS_TEMP = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
    SUITS_TEMP = ["c", "d", "h", "s"]

    r1 = random.choice(RANKS_TEMP)
    r2 = random.choice(RANKS_TEMP)
    s1 = random.choice(SUITS_TEMP)
    s2 = random.choice(SUITS_TEMP)

    # prevent duplicate card
    if r1 == r2 and s1 == s2:
        return random_villain_combo()

    return r1 + s1 + r2 + s2

def blocked(hero_combo, villain_combo):
    return hero_combo[:2] in villain_combo or hero_combo[2:] in villain_combo

def hand_vs_range_equity(
    hero_combo_str: str,
    villain_range_str: str,
    board_str: str = "",
    trials: int = 5000,
):
    hero_hand_str = combo_to_range_token(hero_combo_str)
    res = range_vs_range_equity(
        hero_combo_str,
        villain_range_str,
        board_str,
        trials
    )
    return res

def range_vs_range_equity(
    hero_combos,
    villain_combos_all,
    board_str="",
    trials=50
):
    """
    Optimized equity calculator:
    - hero_combos: list of 2-card hero combos (already expanded)
    - villain_combos_all: list of 2-card villain combos (already expanded & filtered)
    - board_str: string like "AhKdQs" or ""
    - trials: Monte Carlo trials per hero/villain combo pair
    """

    # Parse board once
    board_cards = [board_str[i:i+2] for i in range(0, len(board_str), 2)]

    total_weight = 0
    hero_wins = 0.0
    villain_wins = 0.0
    ties = 0.0

    # Loop hero combos
    for h in hero_combos:

        # Filter villain combos that don't block hero
        villain_combos = [
            v for v in villain_combos_all
            if not blocked(h, v)
        ]

        # Monte Carlo for each villain combo
        for v in villain_combos:
            res = monte_carlo_equity(h, v, board_str, trials)

            total_weight += 1
            hero_wins += res["hero_win"]
            villain_wins += res["villain_win"]
            ties += res["tie"]

    if total_weight == 0:
        return {"hero_win": 0, "villain_win": 0, "tie": 1}

    # Normalize
    hero_eq = hero_wins / total_weight
    villain_eq = villain_wins / total_weight
    tie_eq = ties / total_weight

    return {
        "hero_win": hero_eq,
        "villain_win": villain_eq,
        "tie": tie_eq,
    }

'''
def range_vs_range_equity(
    hero_range_str: str,
    villain_range_str: str,
    board_str: str = "",
    trials: int = 5000,
):
    # 0) Expand hero and villain ranges into hand classes
    hero_classes = expand_range(hero_range_str)

    if villain_range_str != "random":
        villain_classes = expand_range(villain_range_str)
    else:
        villain_classes = []

    # 0a) Expand hero classes → hero combos
    hero_combos = []
    for hc in hero_classes:
        hero_combos.extend(parse_range(hc))

    # 1) Build used_cards BEFORE generating villain
    used_cards = [board_str[i:i + 2] for i in range(0, len(board_str), 2)]

    # 2) Filter hero combos by board blockers
    hero_combos = filter_blocked(hero_combos, used_cards)

    # 3) Build ALL villain combos ONCE (never inside hero loop)
    if villain_classes:
        ALL_VILLAIN_COMBOS = []
        for vc in villain_classes:
            ALL_VILLAIN_COMBOS.extend(parse_range(vc))

        # Deduplicate
        ALL_VILLAIN_COMBOS = list(set(ALL_VILLAIN_COMBOS))
        ALL = ALL_VILLAIN_COMBOS
        rev = [c for c in ALL if c[2:] + c[:2] in ALL]
        
        print(len(ALL_VILLAIN_COMBOS))
        print("Reversed combos:", len(rev))
        print(rev[:20])
        

        # Filter board blockers ONCE
        ALL_VILLAIN_COMBOS = filter_blocked(ALL_VILLAIN_COMBOS, used_cards)

    else:
        # Random villain = full deck
        ALL_VILLAIN_COMBOS = all_2card_combos()

        # Remove board cards
        ALL_VILLAIN_COMBOS = [
            c for c in ALL_VILLAIN_COMBOS
            if not any(card in c for card in used_cards)
        ]

    if not hero_combos or not ALL_VILLAIN_COMBOS:
        raise ValueError("One of the ranges has no valid combos after blocking.")

    # 4) Loop over hero combos (clean, correct)
    results = {}

    for h in hero_combos:

        # Build villain combos *fresh* for this hero combo
        villain_combos = [
            v for v in ALL_VILLAIN_COMBOS
            if not blocked(h, v)
        ]
        print(len(villain_combos))
        total_weight = 0
        hero_wins = 0.0
        villain_wins = 0.0
        ties = 0.0

        for v in villain_combos:

                res = monte_carlo_equity(
                    h,
                    v,
                    board_str,
                    trials
                )

                # weight = 1 for now (can refine later)
                weight = 1
                total_weight += weight

                # assume res = {"hero_win": x, "villain_win": y, "tie": z}
                hero_wins += res["hero_win"]
                villain_wins += res["villain_win"]
                ties += res["tie"]

        if total_weight == 0:
            raise ValueError("No valid hero/villain combo pairs after blocking.")


    # 5) Normalize
    hero_eq = hero_wins / total_weight
    villain_eq = villain_wins / total_weight
    tie_eq = ties / total_weight

    # Cache to CSV if needed
    # Assume h is just 1 Hero hand
    results[hc] = (hero_eq, villain_eq, tie_eq, trials)

    if villain_range_str == "random":
        filename = os.path.join(CACHE_DIR, "random.csv")
    #else
        #check for existing cache file with range

        #print(hero_combos, villain_combos, hero_wins, villain_wins, ties, total_weight)
        cache = load_cache(filename)
        merge_results(cache, results)
        save_cache(filename, cache)

        # print(f"CSV exported: {filename}")

    return {
        "hero_win": hero_eq,
        "villain_win": villain_eq,
        "tie": tie_eq,
    }
'''