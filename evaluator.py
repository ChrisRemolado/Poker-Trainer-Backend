# evaluator.py

RANKS = "23456789TJQKA"
SUITS = "cdhs"

# Unique prime for each rank
PRIMES = {
    "2": 2, "3": 3, "4": 5, "5": 7, "6": 11,
    "7": 13, "8": 17, "9": 19, "T": 23,
    "J": 29, "Q": 31, "K": 37, "A": 41
}

def card_to_int(card):
    """Convert 'As' → (rank_index, suit_index, prime)."""
    r, s = card[0], card[1]
    return (RANKS.index(r), SUITS.index(s), PRIMES[r])

def prime_product(cards_int):
    """Multiply primes of all 7 cards → unique rank fingerprint."""
    product = 1
    for _, _, p in cards_int:
        product *= p
    return product

def rank_counts_from_primes(cards_int):
    """
    Convert prime product → rank counts.
    (We do it directly for clarity, but the idea is prime factorization.)
    """
    ranks = [r for r, _, _ in cards_int]
    counts = {r: ranks.count(r) for r in set(ranks)}
    return counts

def rank_mask(cards_int):
    """13-bit mask: bit i = 1 if rank i appears."""
    mask = 0
    for r,_,_ in cards_int:
        mask |= (1 << r)
    return mask

def rank_mask_rank_only(ranks):
    mask = 0
    for r in ranks:
        mask |= (1 << r)
    return mask


def detect_straight(mask):
    """
        Detect a straight from a 13-bit rank mask.
        Returns the high-card rank index, or None.
        """

    # Wheel: A-2-3-4-5
    wheel = (1 << 12) | 0b1111  # A + 2,3,4,5 (wheel = 0b1000000001111)
    if (mask & wheel) == wheel:
        return 3  # 5-high straight

    # Normal straights: high card from A (12) down to 5 (4)
    for high in range(12, 3, -1):
        window = 0b11111 << (high - 4)
        if (mask & window) == window:
            return high

    return None

def detect_straight_from_mask(mask):
    """
    Given a 13-bit rank mask (ONLY for suited cards),
    detect the highest straight inside it.
    Returns the high-card rank index, or None.
    """

    # Extract ranks present in the mask
    ranks = [r for r in range(13) if (mask & (1 << r))]
    if len(ranks) < 5:
        return None

    # Sort high → low
    ranks.sort(reverse=True)

    # Normal straights (e.g., T-9-8-7-6)
    for i in range(len(ranks) - 4):
        window = ranks[i:i+5]

        # Must be exactly 5 distinct ranks
        if len(window) != 5:
            continue

        # Check if consecutive
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return window[0]  # high card of straight

    # Wheel straight (A-2-3-4-5)
    wheel = {12, 3, 2, 1, 0}
    if wheel.issubset(ranks):
        return 3  # 5-high straight

    return None


def evaluate_7(cards):
    """
    Prime-multiplication evaluator.
    Returns (category, tiebreakers...) where lower = stronger.
    """

    # Convert cards
    cards_int = cards
    ranks = [r for r, _, _ in cards_int]

    # STEP 1 — PRIME MULTIPLICATION
    product = prime_product(cards_int)

    # STEP 2 — RANK COUNTS (derived from prime factorization idea)
    counts = rank_counts_from_primes(cards_int)

    # Group ranks by multiplicity
    groups = {}
    for r, c in counts.items():
        groups.setdefault(c, []).append(r)
    for g in groups.values():
        g.sort(reverse=True)

    # STEP 3 — SUIT COUNTS (flush detection)
    suit_counts = {}
    for _, s, _ in cards_int:
        suit_counts[s] = suit_counts.get(s, 0) + 1

    # Pick the suit with the most cards
    flush_suit = max(suit_counts, key=suit_counts.get)

    # Only keep it if it actually has 5+
    if suit_counts[flush_suit] < 5:
        flush_suit = None

    # STEP 4 — STRAIGHT DETECTION (bitmask)
    mask = rank_mask(cards_int)
    straight_high = detect_straight(mask)

    # STEP 5 — STRAIGHT FLUSH
    if flush_suit is not None:
        # extract only ranks for the suited cards
        suited_ranks = [rank for (rank, suit, prime) in cards_int if suit == flush_suit]

        if len(suited_ranks) >= 5:
            sf_mask = rank_mask_rank_only(suited_ranks)
            sf_high = detect_straight_from_mask(sf_mask)

            if sf_high is not None:
                return (0, -sf_high)

    # STEP 6 — QUADS
    if 4 in groups:
        quad = groups[4][0]
        kicker = max(r for r in ranks if r != quad)
        return (1, -quad, -kicker)

    # STEP 7 — FULL HOUSE
    if 3 in groups and (len(groups[3]) > 1 or 2 in groups):
        trips = groups[3][0]
        if len(groups[3]) > 1:
            pair = groups[3][1]
        else:
            pair = groups[2][0]
        return (2, -trips, -pair)

    # STEP 8 — FLUSH
    if flush_suit is not None:
        suited_ranks = [rank for (rank, suit, prime) in cards_int if suit == flush_suit]
        if len(suited_ranks) >= 5:
            # sort high → low
            suited_ranks.sort(reverse=True)

            # take best 5
            top5 = suited_ranks[:5]

            # return proper comparison tuple
            return (3, -top5[0], -top5[1], -top5[2], -top5[3], -top5[4])

    # STEP 9 — STRAIGHT
    mask = rank_mask(cards_int)
    straight_high = detect_straight(mask)
    if straight_high is not None:
        return (4, -straight_high)

    # STEP 10 — TRIPS
    if 3 in groups:
        trip = groups[3][0]
        kickers = sorted([r for r in ranks if r != trip], reverse=True)[:2]
        return (5, -trip, *[-k for k in kickers])

    # STEP 11 — TWO PAIR
    if 2 in groups and len(groups[2]) >= 2:
        p1, p2 = groups[2][:2]
        kicker = max(r for r in ranks if r not in (p1, p2))
        return (6, -p1, -p2, -kicker)

    # STEP 12 — ONE PAIR
    if 2 in groups:
        p = groups[2][0]
        kickers = sorted([r for r in ranks if r != p], reverse=True)[:3]
        return (7, -p, *[-k for k in kickers])

    # STEP 13 — HIGH CARD
    top5 = sorted(ranks, reverse=True)[:5]
    return (8, *[-k for k in top5])