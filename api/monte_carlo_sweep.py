#from main import *
from .evaluator_v1 import *

import random
from itertools import combinations

import csv

RANKS = "23456789TJQKA"
SUITS = "cdhs"

def card_to_int(card: str):
    """Convert 'As' into evaluator tuple (rank_index, suit_index, prime)."""
    r = card[0]
    s = card[1]
    rank_index = RANKS.index(r)   # 2=0 ... A=12
    suit_index = SUITS.index(s)
    prime = PRIMES[rank_index]
    return (rank_index, suit_index, prime)

def all_cards():
    return [r + s for r in RANKS for s in SUITS]

def simulate_vs_random_villain(hero_hand, trials=5000):
    """
    hero_hand: ['As', 'Kd']
    trials: number of random boards/villain hands
    Returns: (hero_win_pct, villain_win_pct, tie_pct)
    """

    deck = all_cards()
    hero_set = set(hero_hand)

    hero_wins = villain_wins = ties = 0

    for _ in range(trials):

        # 1. Remove hero cards from deck
        remaining = [c for c in deck if c not in hero_set]

        # 2. Sample villain hand from remaining
        villain_hand = random.sample(remaining, 2)

        # 3. Remove villain cards from remaining
        remaining = [c for c in remaining if c not in villain_hand]

        # 4. Sample board from remaining
        board = random.sample(remaining, 5)

        # 5. Convert to evaluator format
        hero_int = [card_to_int(c) for c in hero_hand + board]
        villain_int = [card_to_int(c) for c in villain_hand + board]

        # 6. Evaluate
        hero_rank = evaluate_7(hero_int)
        villain_rank = evaluate_7(villain_int)

        # 7. Compare
        if hero_rank < villain_rank:
            hero_wins += 1
        elif villain_rank < hero_rank:
            villain_wins += 1
        else:
            ties += 1

    total = hero_wins + villain_wins + ties
    return (hero_wins / total, villain_wins / total, ties / total)

def all_starting_hands():
    deck = all_cards()
    return list(combinations(deck, 2))  # 1326 combos

def sweep_all_preflop(trials_per_hand=3000, sample=None):
    """
    Runs Monte Carlo vs random villain for each starting hand.
    If sample is not None, randomly sample that many hero hands instead of all 1326.
    Returns: dict[(card1, card2)] = (hero_win_pct, villain_win_pct, tie_pct)
    """
    hands = all_starting_hands()
    if sample is not None:
        hands = random.sample(hands, sample)

    results = {}
    for i, hero in enumerate(hands, 1):
        hero_list = list(hero)
        hw, vw, t = simulate_vs_random_villain(hero_list, trials=trials_per_hand)
        results[hero] = (hw, vw, t)

        if i % 50 == 0:
            print(f"{i}/{len(hands)} done")

    return results

def export_results_to_csv(results, filename="preflop_equity_sweep.csv"):
    """
    results: dict with keys = (card1, card2)
             values = (hero_win_pct, villain_win_pct, tie_pct)
    filename: output CSV file name
    """
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hand", "hero_win", "villain_win", "tie"])

        for (c1, c2), (hw, vw, t) in results.items():
            hand_str = c1 + c2
            writer.writerow([hand_str, hw, vw, t])

    print(f"CSV exported: {filename}")
