# range_parser.py
from .hand_constants import ALL_169_HANDS
1
RANKS = "23456789TJQKA"
SUITS = "cdhs"


# -----------------------------
# Combo generators
# -----------------------------
def canonical(c1, c2):
    return tuple(sorted([c1, c2]))

def generate_suited(r1: str, r2: str) -> list[str]:
    combos = []
    for s in SUITS:
        c1 = r1 + s
        c2 = r2 + s
        a, b = canonical(c1, c2)
        combos.append(a + b)
    return combos


def generate_offsuit(r1: str, r2: str) -> list[str]:
    combos = []
    for s1 in SUITS:
        for s2 in SUITS:
            if s1 != s2:
                c1 = r1 + s1
                c2 = r2 + s2
                a, b = canonical(c1, c2)
                combos.append(a + b)
    return combos


def generate_pair(r: str) -> list[str]:
    combos = []
    for i, s1 in enumerate(SUITS):
        for s2 in SUITS[i + 1:]:
            c1 = r + s1
            c2 = r + s2
            a, b = canonical(c1, c2)
            combos.append(a + b)
    return combos


def generate_all_combos() -> list[str]:
    combos = []
    deck = [r + s for r in RANKS for s in SUITS]

    for i in range(len(deck)):
        for j in range(i + 1, len(deck)):
            c1 = deck[i]
            c2 = deck[j]
            # canonical order: lexicographically sorted
            a, b = sorted([c1, c2])
            combos.append(a + b)

    return combos


def hand_class_from_str(combo: str) -> str:
    r1, s1 = combo[0], combo[1]
    r2, s2 = combo[2], combo[3]

    rank_order = "23456789TJQKA"
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1

    if r1 == r2:
        return r1 + r2

    suited = "s" if s1 == s2 else "o"
    return r1 + r2 + suited


# -----------------------------
# Core token expansion
# -----------------------------

def expand_range(range_str: str) -> list[str]:
    """
    Expand a full range string like 'A2s+, KQo, 55+' into a list of
    canonical 169-hand classes (e.g., ['A2s','A3s',...]).
    """
    if not range_str:
        return []

    tokens = [t.strip() for t in range_str.split(",") if t.strip()]
    hands: list[str] = []

    for token in tokens:
        if token.lower() == "random":
            hands.extend(ALL_169_HANDS)
        else:
            hands.extend(expand_hand_classes(token))

    return hands


def expand_hand_classes(token: str) -> list[str]:
    token = token.strip()

    # 1. Pocket pair (e.g., 55)
    if len(token) == 2 and token[0] == token[1]:
        return [token]

    # 2. Exact suited/offsuit (AKs, AKo)
    if len(token) == 3 and token[2] in ("s", "o"):
        return [token]

    # 3. Plus notation (55+, A2s+, KTo+)
    if token.endswith("+"):
        base = token[:-1]

        # Pair plus (55+)
        if len(base) == 2 and base[0] == base[1]:
            start = RANKS.index(base[0])
            return [r+r for r in RANKS[start:]]

        # Suited/offsuit plus (A2s+, KTo+)
        r1, r2, suitedness = base[0], base[1], base[2]
        start = RANKS.index(r2)
        return [r1 + RANKS[i] + suitedness for i in range(start, len(RANKS))]

    # 4. Dash notation (A2s-A5s, 22-66)
    if "-" in token:
        lo, hi = token.split("-")

        # Pair range (22-66)
        if len(lo) == 2 and len(hi) == 2 and lo[0] == lo[1] == hi[0] == hi[1]:
            start = RANKS.index(lo[0])
            end = RANKS.index(hi[0])
            return [RANKS[i] + RANKS[i] for i in range(start, end+1)]

        # Suited/offsuit range (A2s-A5s)
        r1, suitedness = lo[0], lo[2]
        start = RANKS.index(lo[1])
        end = RANKS.index(hi[1])
        return [r1 + RANKS[i] + suitedness for i in range(start, end+1)]

    # 5. Exact hand without suitedness (AK → AKs + AKo)
    if len(token) == 2:
        r1, r2 = token[0], token[1]
        if r1 == r2:
            return [token]
        return [r1 + r2 + "s", r1 + r2 + "o"]

    raise ValueError(f"Invalid range token: {token}")


def expand_hand_notation(raw_token: str) -> list[str]:
    """
    Supported syntax:
      - random

      - A2s+
      - KTo+
      - 55+

      - 22-66
      - A2s-A5s
      - KTo-KQo

      - 22
      - AKs
      - AKo
      - AK  (both suited + offsuit)
    """
    # normalize aggressively
    token = (
        raw_token.strip()
        .replace("\r", "")
        .replace("\n", "")
        .replace(" ", "")
    )

    if not token:
        return []

    # RANDOM
    if token.lower() == "random":
        return generate_all_combos()

    # -----------------
    # PLUS HANDS
    # -----------------
    if token.endswith("+"):
        base = token[:-1]

    # pair with plus: K9s+
    if len(token) == 4 and token[2] == "s" and token[3] == "+":
        r1 = token[0]  # 'K'
        start_rank = token[1]  # '9'
        start = RANKS.index(start_rank)
        end = RANKS.index("A")  # kicker goes from 9,T,J,Q,A
        combos = []

        for i in range(start, end + 1, 1):  # 2..K order, so this is low→high
            if i != RANKS.index(r1):
                combos += generate_suited(r1, RANKS[i])
        return combos

    # pair with plus: K2o+
    if len(token) == 4 and token[2] == "o" and token[3] == "+":
        r1 = token[0] # 'K'
        r2 = token[1] # '2'
        start = RANKS.index(r2)
        skip = RANKS.index(r1)
        end = RANKS.index("A")
        combos = []

        for i in range(start, end, 1):  # 2..K order, so this is low→high
            if i != RANKS.index(r1):
                combos += generate_offsuit(r1, RANKS[i])
        print (combos)
        return combos

    # pair with plus: JJ+
    if len(token) == 3 and token[0] == token[1] and token[2] == "+":
        r = token[0]
        start = RANKS.index(r)
        combos = []
        for i in range(start, len(RANKS)):  # 2..A order, so this is low→high
            combos += generate_pair(RANKS[i])
        return combos

    # -----------------
    # RANGED HANDS
    # -----------------

    # suited range: A2s-A5s
    if "-" in token and token.endswith("s"):
        left, right = token.split("-", 1)
        left = left.strip()
        right = right.strip()

        if len(left) != 3 or len(right) != 3:
            raise ValueError(f"Invalid suited range token: {raw_token}")

        r1 = left[0]
        start_rank = left[1]
        end_rank = right[1]

        if r1 not in RANKS or start_rank not in RANKS or end_rank not in RANKS:
            raise ValueError(f"Invalid ranks in suited range: {raw_token}")

        start = RANKS.index(start_rank)
        end = RANKS.index(end_rank)
        if start < end:
            # e.g. A5s-A2s is invalid in this simple syntax
            raise ValueError(f"Suited range must be low-to-high: {raw_token}")

        combos = []
        # RANKS is high→low, so iterate from start down to end
        for i in range(start, end - 1, -1):
            combos += generate_suited(r1, RANKS[i])
        return combos

    # offsuit range: KTo-KQo
    if "-" in token and token.endswith("o"):
        left, right = token.split("-", 1)
        left = left.strip()
        right = right.strip()

        if len(left) != 3 or len(right) != 3:
            raise ValueError(f"Invalid offsuit range token: {raw_token}")

        r1 = left[0]
        start_rank = left[1]
        end_rank = right[1]

        if r1 not in RANKS or start_rank not in RANKS or end_rank not in RANKS:
            raise ValueError(f"Invalid ranks in offsuit range: {raw_token}")

        start = RANKS.index(start_rank)
        end = RANKS.index(end_rank)
        if start < end:
            raise ValueError(f"Offsuit range must be low-to-high: {raw_token}")

        combos = []
        for i in range(start, end - 1, -1):
            combos += generate_offsuit(r1, RANKS[i])
        return combos

    # pair range: 22-66
    if "-" in token and len(token) == 5:
        left, right = token.split("-", 1)
        if len(left) == 2 and len(right) == 2 and left[0] == left[1] and right[0] == right[1]:
            start_rank = left[0]
            end_rank = right[0]
            if start_rank not in RANKS or end_rank not in RANKS:
                raise ValueError(f"Invalid ranks in pair range: {raw_token}")

            start = RANKS.index(start_rank)
            end = RANKS.index(end_rank)
            if start < end:
                raise ValueError(f"Pair range must be low-to-high: {raw_token}")

            combos = []
            for i in range(start, end - 1, -1):
                combos += generate_pair(RANKS[i])
            return combos

    # -----------------
    # EXACT HANDS
    # -----------------

    # pocket pair: 22
    if len(token) == 2:
        r1, r2 = token[0], token[1]
        if r1 not in RANKS or r2 not in RANKS:
            raise ValueError(f"Invalid ranks in mixed token: {raw_token}")
        if r1 == r2:
            return generate_pair(r1)

    # exact suited: AKs
    if len(token) == 3 and token.endswith("s"):
        r1, r2 = token[0], token[1]
        if r1 not in RANKS or r2 not in RANKS:
            raise ValueError(f"Invalid ranks in suited token: {raw_token}")
        return generate_suited(r1, r2)

    # exact offsuit: AKo
    if len(token) == 3 and token.endswith("o"):
        r1, r2 = token[0], token[1]
        if r1 not in RANKS or r2 not in RANKS:
            raise ValueError(f"Invalid ranks in offsuit token: {raw_token}")
        return generate_offsuit(r1, r2)

    # exact mixed: AK (both suited + offsuit)
    if len(token) == 2:
        r1, r2 = token[0], token[1]
        if r1 not in RANKS or r2 not in RANKS:
            raise ValueError(f"Invalid ranks in mixed token: {raw_token}")
        return generate_suited(r1, r2) + generate_offsuit(r1, r2)

    raise ValueError(f"Unrecognized range token: {raw_token}")

# -----------------------------
# Public API
# -----------------------------

def parse_range(range_str: str) -> list[str]:
    if range_str is None:
        return []

    tokens = [t for t in range_str.split(",") if t.strip()]
    raw: list[str] = []

    for t in tokens:
        raw += expand_hand_notation(t)

    # Canonicalize and dedupe here
    norm: list[str] = []
    for c in raw:
        if len(c) != 4:
            continue  # ignore malformed
        c1, c2 = c[:2], c[2:]
        if c1 == c2:
            continue  # drop illegal same-card combos
        a, b = sorted([c1, c2])
        norm.append(a + b)

    return list(set(norm))
