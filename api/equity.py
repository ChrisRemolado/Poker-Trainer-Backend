from .monte_carlo_sweep import card_to_int
from .evaluator_v1 import RANKS, SUITS, PRIMES, evaluate_7
import random

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def split_cards(s: str):
    """Convert 'As2s' or ['As','2s'] into ['As','2s'] safely."""
    if isinstance(s, list):
        return s
    s = s.strip().replace(" ", "").replace(",", "")
    return [s[i:i+2] for i in range(0, len(s), 2) if len(s[i:i+2]) == 2]

def deck():
    """Evaluator‑aligned deck."""
    return [r + s for r in RANKS for s in SUITS]


# ---------------------------------------------------------
# FINAL MONTE CARLO EQUITY
# ---------------------------------------------------------

def monte_carlo_equity(hero, villain, board, trials):
    hero_wins = villain_wins = ties = 0

    # Normalize inputs
    hero_cards = split_cards(hero)
    villain_cards = split_cards(villain)
    board_cards = split_cards(board)

    # Convert to evaluator ints once
    hero_int = [card_to_int(c) for c in hero_cards]
    villain_int = [card_to_int(c) for c in villain_cards]
    board_int = [card_to_int(c) for c in board_cards]

    for _ in range(trials):

        # Build remaining deck from explicit card list
        used = set(hero_cards + villain_cards + board_cards)
        d = [c for c in deck() if c not in used]
        random.shuffle(d)

        # Complete board
        missing = 5 - len(board_cards)
        runout = d[:missing]
        runout_int = [card_to_int(c) for c in runout]

        full_board = board_int + runout_int

        # Evaluate
        hero_score = evaluate_7(hero_int + full_board)
        villain_score = evaluate_7(villain_int + full_board)

        # Lower tuple = stronger hand
        if hero_score < villain_score:
            hero_wins += 1
        elif hero_score == villain_score:
            ties += 1
        else:
            villain_wins += 1

    return {
        "hero_win": hero_wins / trials,
        "villain_win": villain_wins / trials,
        "tie": ties / trials
    }