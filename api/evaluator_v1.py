# evaluator.py
import itertools

RANKS = "23456789TJQKA"
SUITS = "cdhs"
PRIMES = [
    2, 3, 5, 7, 11, 13, 17,
    19, 23, 29, 31, 37, 41
]
# index 0 = rank 2, index 12 = Ace

# HELPERS
def sorted_ranks_desc(counts):
    ranks = []
    for r in range(12, -1, -1):  # A → 2
        ranks.extend([r] * counts[r])
    return ranks

def shape(counts):
    # list of (count, rank), sorted by count then rank
    return sorted(
        [(counts[r], r) for r in range(13) if counts[r] > 0],
        key=lambda x: (-x[0], -x[1])
    )


def prime_product(cards_int):
    prod_p = 1
    for r, _, _ in cards_int:
        prod_p *= PRIMES[r]
    return prod_p

def decode_prime_product(prod):
    counts = [0]*13
    for r in range(13):
        p = PRIMES[r]
        while prod % p == 0:
            counts[r] += 1
            prod //= p
    return counts

def rank_counts(cards_int):
    """
    Given a list of 7 cards in internal form (rank_index, suit_index, prime),
    return a 13-element list where index r is the count of rank r in the hand.
    """
    counts = [0] * 13
    for r, _, _ in cards_int:
        counts[r] += 1
    return counts

def rank_mask(cards_int):
    mask = 0
    for r, _, _ in cards_int:
        mask |= (1 << r)
    return mask

def suit_mask(cards_int):
    # returns list of 4 masks, one per suit
    suits = [0, 0, 0, 0]
    for r, s, _ in cards_int:
        suits[s] |= (1 << r)
    return suits

def suited_rank_mask(cards_int, suit):
    mask = 0
    for r, s, _ in cards_int:
        if s == suit:
            mask |= (1 << r)
    return mask

def normalize(category, ranks):
    # ranks = descending real ranks
    neg = [-r for r in ranks]
    padded = neg + [0] * (6 - len(neg))
    return (category, *padded)

# FUNCTIONS STRAIGHTS & FLUSHES
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

def detect_flush(cards_int):
    """
        suit_masks: list of 4 rank masks (one per suit).
        Returns suit index (0–3) or None.
    """
    suit_counts = [0, 0, 0, 0]

    for _, s, _ in cards_int:
        suit_counts[s] += 1

    # Find any suit with 5+ cards
    for s in range(4):
        if suit_counts[s] >= 5:
            return s

    return None

# FUNCTION: HAND-TUPLE
def hand_tuple(cards_int, category, straight_high=None, flush_suit=None):
    counts = rank_counts(cards_int)
    sh = shape(counts)
    kickers = sorted_ranks_desc(counts)

    # CATEGORY ORDER (lower = stronger)
    # 0 = straight flush
    # 1 = four of a kind
    # 2 = full house
    # 3 = flush
    # 4 = straight
    # 5 = three of a kind
    # 6 = two pair
    # 7 = one pair
    # 8 = high card

    if category == 0:  # straight flush
        return normalize(0, [straight_high])

    if category == 1:  # quads
        quad_rank = sh[0][1]
        kicker = kickers[0]
        return normalize(1, [quad_rank, kicker])


    if category == 2:  # full house
        trips = sh[0][1]
        pair = sh[1][1]
        return normalize(2, [trips, pair])

    if category == 3:  # flush
        flush_ranks = sorted(
            [r for r, s, _ in cards_int if s == flush_suit],
            reverse=True
        )[:5]
        return normalize(3, flush_ranks[:5])

    if category == 4:  # straight
        return normalize(4, [straight_high])

    if category == 5:  # trips
        trips = sh[0][1]
        k1, k2 = [k for k in kickers if k != trips][:2]
        return normalize(5, [trips, k1, k2])

    if category == 6:  # two pair
        high_pair = sh[0][1]
        low_pair = sh[1][1]
        kicker = [k for k in kickers if k not in (high_pair, low_pair)][0]  # highest remaining rank
        return normalize(6, [high_pair, low_pair, kicker])

    if category == 7:  # one pair
        pair = sh[0][1]
        k1, k2, k3 = [k for k in kickers if k != pair][:3]
        return normalize(7, [pair, k1, k2, k3])

    if category == 8:  # high card
        return normalize(8, kickers[:5])


# FUNCTION: EVALUATOR
def evaluate_7(cards_int):
    # 0. Sort hands
    #cards_int = sorted(cards_int, reverse=True)

    # 1. Prime product → rank counts
    product = prime_product(cards_int)
    counts = decode_prime_product(product)
    sh = shape(counts)

    # 2. Straight + flush detection
    rmask = rank_mask(cards_int)
    straight_high = detect_straight(rmask)

    flush_suit = detect_flush(cards_int)
    if flush_suit is not None:
        suited_mask = suited_rank_mask(cards_int, flush_suit)
        sf_high = detect_straight_from_mask(suited_mask)
        if sf_high is not None:
            return hand_tuple(cards_int, 0, straight_high=sf_high)

    # 3. Use prime‑decoded shape to classify rank patterns
    if sh[0][0] == 4:
        return hand_tuple(cards_int, 1)

    if sh[0][0] == 3 and sh[1][0] >= 2:
        return hand_tuple(cards_int, 2)

    if flush_suit is not None:
        return hand_tuple(cards_int, 3, flush_suit=flush_suit)

    if straight_high is not None:
        return hand_tuple(cards_int, 4, straight_high=straight_high)

    if sh[0][0] == 3:
        return hand_tuple(cards_int, 5)

    if sh[0][0] == 2 and sh[1][0] == 2:
        return hand_tuple(cards_int, 6)

    if sh[0][0] == 2:
        return hand_tuple(cards_int, 7)

    return hand_tuple(cards_int, 8)
