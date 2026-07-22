import csv, random
from collections import defaultdict

RANKS = "23456789TJQKA"
SUITS = "cdhs"

def class_to_random_combo(cls):
    """
    Convert a class like 'K2s', 'Q3o', 'TT' into a random valid 2-card combo
    consistent with that class.
    """

    r1 = cls[0]
    r2 = cls[1]
    suited_flag = cls[2] if len(cls) == 3 else None

    # --- Case 1: Pair (e.g., 'TT') ---
    if r1 == r2:
        # choose 2 distinct suits
        s1, s2 = random.sample(SUITS, 2)
        return [r1 + s1, r2 + s2]

    # --- Case 2: Suited (e.g., 'K2s') ---
    if suited_flag == "s":
        suit = random.choice(SUITS)
        return [r1 + suit, r2 + suit]

    # --- Case 3: Offsuit (e.g., 'K2o') ---
    if suited_flag == "o":
        s1 = random.choice(SUITS)
        s2 = random.choice([s for s in SUITS if s != s1])
        return [r1 + s1, r2 + s2]

    # --- Case 4: No suitedness specified (rare) ---
    # treat as "any combo"
    s1 = random.choice(SUITS)
    s2 = random.choice(SUITS)
    while r1 == r2 and s1 == s2:
        s2 = random.choice(SUITS)
    return [r1 + s1, r2 + s2]

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

def aggregate_1326_to_169(input_csv):
    buckets = defaultdict(list)

    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hand = row["hand"]
            hw = float(row["hero_win"])
            vw = float(row["villain_win"])
            t  = float(row["tie"])

            cls = hand_class_from_str(hand)
            buckets[cls].append((hw, vw, t))

    aggregated = {}
    for cls, vals in buckets.items():
        n = len(vals)
        avg_hw = sum(v[0] for v in vals) / n
        avg_vw = sum(v[1] for v in vals) / n
        avg_t  = sum(v[2] for v in vals) / n
        aggregated[cls] = (avg_hw, avg_vw, avg_t)

    return aggregated

def export_169_csv(agg, filename="preflop_169_equity.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hand_class", "hero_win", "villain_win", "tie"])

        # canonical 169 ordering
        order = []
        for r1 in reversed(RANKS):          # A → 2
            for r2 in reversed(RANKS):      # A → 2
                if r1 == r2:
                    order.append(r1 + r2)
                else:
                    order.append(r1 + r2 + "s")
                    order.append(r1 + r2 + "o")

        for cls in order:
            if cls in agg:
                hw, vw, t = agg[cls]
                writer.writerow([cls, hw, vw, t])

    print(f"169-hand CSV exported: {filename}")

def load_169_csv(path):
    data = {}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row["hand_class"]
            hw = float(row["hero_win"])
            data[cls] = hw
    return data

def compute_drift(yours, reference):
    drift = {}
    for cls in reference:
        if cls in yours:
            diff = yours[cls] - reference[cls]
            pct = diff / reference[cls] if reference[cls] != 0 else 0
            drift[cls] = (diff, pct)
    return drift


def rank_drift(drift):
    return sorted(
        drift.items(),
        key=lambda x: abs(x[1][0]),   # sort by absolute error
        reverse=True
    )

def print_drift_report(ranked, top=25):
    print("=== DRIFT REPORT (Top Errors) ===")
    print("Hand   YourEq  RefEq  Diff   Pct")
    print("------------------------------------")

    for cls, (diff, pct) in ranked[:top]:
        print(f"{cls:4}  {diff:+.4f}  ({pct:+.2%})")

def drift_detector(your_csv, ref_csv, top=25):
    yours = load_169_csv(your_csv)
    ref   = load_169_csv(ref_csv)

    drift = compute_drift(yours, ref)
    ranked = rank_drift(drift)

    print_drift_report(ranked, top=top)

    return ranked

