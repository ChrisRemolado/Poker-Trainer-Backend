from api.monte_carlo_sweep import *
from drift_heatmap import *
from fastapi import *
'''
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
'''
from aggregator_169 import *

app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def deck():
    ranks = "23456789TJQKA"
    suits = "cdhs"
    return [r + s for r in ranks for s in suits]

class EquityRequest(BaseModel):
    hero: list[str]
    villain: list[str]
    board: list[str] = []
    trials: int = 10000

def card_to_int(card):
    """Convert 'As' → (rank_index, suit_index, prime)."""

    # Case 1: Already a 2-character string like "As"
    if isinstance(card, str) and len(card) == 2:
        r, s = card[0], card[1]

    # Case 2: Tuple or list like ('A','s') or ['A','s']
    elif isinstance(card, (tuple, list)) and len(card) == 2:
        r, s = card[0], card[1]

    # Case 3: List like ['As']
    elif isinstance(card, list) and len(card) == 1 and isinstance(card[0], str) and len(card[0]) == 2:
        r, s = card[0][0], card[0][1]

    else:
        raise ValueError(f"Unrecognized card format: {card}")

    rank_index = RANKS.index(r)
    suit_index = SUITS.index(s)

    return (rank_index, suit_index, PRIMES[rank_index])

def normalize(cards):
    fixed = []
    for c in cards:
        c = c.strip()
        if len(c) != 2:
            raise ValueError(f"Invalid card: {c}")
        rank = c[0].upper()
        suit = c[1].lower()
        fixed.append(rank + suit)
    return fixed

def random_hand(deck):
    deck = list(deck)  # ensure it's a list
    return random.sample(deck, 2)

def monte_carlo_equity(hero, villain, board, trials):
    # wins = ties = 0
    hero_wins = villain_wins = ties = 0

    if hero is None:
        hero = random_hand(deck())
    if villain is None:
        remaining = [c for c in deck() if c not in hero]
        villain = random_hand(remaining)

    hero_int = [card_to_int(c) for c in hero]
    villain_int = [card_to_int(c) for c in villain]
    board_int = [card_to_int(c) for c in board]

    for _ in range(trials):
        # Build remaining deck (now correct)
        d = [c for c in deck() if c not in hero + villain + board]
        random.shuffle(d)

        missing = 5 - len(board)
        runout = d[:missing]
        runout_int = [card_to_int(c) for c in runout]

        full_board = board_int + runout_int

        hero_score = evaluate_7(hero_int + full_board)
        villain_score = evaluate_7(villain_int + full_board)

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

'''
        if hero_score < villain_score:
            wins += 1
        elif hero_score == villain_score:
            ties += 1
        
    print(wins, " ", ties, " ", trials-wins-ties)
    return (wins + 0.5 * ties) / trials
'''

if __name__ == "__main__":
    # Full 1326-hand sweep (warning: slow)
    results = sweep_all_preflop(trials_per_hand=500)

    # Export to CSV
    export_results_to_csv(results, "preflop_equity_sweep.csv")

    agg = aggregate_1326_to_169("preflop_equity_sweep.csv")
    export_169_csv(agg, "preflop_169_equity.csv")

    yours = load_169_csv("preflop_169_equity.csv")
    ref   = load_169_csv("reference_169_equity.csv")

    drift_dict = compute_drift_dict(yours, ref)
    drift_mat  = build_drift_matrix(drift_dict)


    plot_drift_heatmap(drift_mat)
    print(drift_mat.max(), drift_mat.min())



@app.post("/equity")
def compute_equity(req: EquityRequest):
    eq = monte_carlo_equity(req.hero, req.villain, req.board, req.trials)
    return {"equity": eq}

