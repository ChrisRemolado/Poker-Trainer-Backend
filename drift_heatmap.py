import csv
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

RANKS = "23456789TJQKA"
RANK_TO_IDX = {r: i for i, r in enumerate(RANKS)}

def load_169_csv(path):
    data = {}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row["hand_class"]
            hw = float(row["hero_win"])
            data[cls] = hw
    return data

def compute_drift_dict(yours, reference):
    drift = {}
    for cls, ref_eq in reference.items():
        if cls in yours:
            your_eq = yours[cls]
            drift[cls] = your_eq - ref_eq   # positive = you overestimate
    return drift

def init_drift_matrix():
    # 13x13, NaN for missing
    mat = np.full((13, 13), np.nan)
    return mat

def place_in_matrix(mat, hand_class, value):
    # hand_class: e.g. "AKs", "QJo", "TT"
    r1 = hand_class[0]
    r2 = hand_class[1]
    suited = (len(hand_class) == 3 and hand_class[2] == "s")
    offsuit = (len(hand_class) == 3 and hand_class[2] == "o")

    i = 12 - RANK_TO_IDX[r1]  # A at top
    j = 12 - RANK_TO_IDX[r2]  # A at left

    if r1 == r2:
        # pair on diagonal
        mat[i, j] = value
    elif suited:
        # suited in upper triangle (row < col)
        if i < j:
            mat[i, j] = value
        else:
            mat[j, i] = value
    elif offsuit:
        # offsuit in lower triangle (row > col)
        if i > j:
            mat[i, j] = value
        else:
            mat[j, i] = value

def build_drift_matrix(drift_dict):
    mat = init_drift_matrix()
    for cls, val in drift_dict.items():
        place_in_matrix(mat, cls, val)
    return mat

def plot_drift_heatmap(mat: object, title: object = "Equity Drift (yours - reference)") -> None:
    ranks_display = list(reversed(RANKS))  # A K Q ... 2

    plt.figure(figsize=(8, 7))
    sns.heatmap(
        mat,
        annot=False,
        cmap="coolwarm",
        center=0.0,
        xticklabels=ranks_display,
        yticklabels=ranks_display,
        square=True
    )
    plt.xlabel("Second card rank")
    plt.ylabel("First card rank")
    plt.title(title)
    plt.tight_layout()
    plt.show()
