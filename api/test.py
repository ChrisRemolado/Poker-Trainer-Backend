from .evaluator_v1 import RANKS, SUITS, PRIMES, evaluate_7
from .equity import monte_carlo_equity

def split_cards(s: str):
    s = s.strip().replace(" ", "").replace(",", "")
    out = []
    for i in range(0, len(s), 2):
        c = s[i:i+2]
        if len(c) == 2:
            out.append(c)
    return out

def card_to_int_local(card: str):
    print("ENCODING CARD:", repr(card))  # <--- KEY LINE
    r = card[0]
    s = card[1]
    return (RANKS.index(r), SUITS.index(s), PRIMES[RANKS.index(r)])

def debug_one_spot():
    hero = "As2s"
    villain = "KcQd"
    board = "7h8c9dThJc"

    hero_cards = split_cards(hero)
    villain_cards = split_cards(villain)
    board_cards = split_cards(board)

    print("HERO_CARDS:", hero_cards)
    print("VILLAIN_CARDS:", villain_cards)
    print("BOARD_CARDS:", board_cards)

    hero_int = [card_to_int_local(c) for c in hero_cards]
    villain_int = [card_to_int_local(c) for c in villain_cards]
    board_int = [card_to_int_local(c) for c in board_cards]

    print("HERO_INT:", hero_int)
    print("VILLAIN_INT:", villain_int)
    print("BOARD_INT:", board_int)

    print("HERO_SCORE:", evaluate_7(hero_int + board_int))
    print("VILLAIN_SCORE:", evaluate_7(villain_int + board_int))

debug_one_spot()
print(
    monte_carlo_equity("As2s+", "KcQd", "", 10)
    )