# api/server.py
import csv
import datetime
import json
import os
from sqlite3.dbapi2 import Date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union, List, Dict
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor, as_completed

from .equity import monte_carlo_equity
from .range_equity import *
from .range_parser import expand_range, expand_hand_notation, parse_range
from .hand_constants import ALL_169_HANDS

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

app = FastAPI(title="Poker Equity API")
VALID_RANKS = set("23456789TJQKA")
VALID_SUITS = set("cdhs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://luxpokertrainer.vercel.app",
        "http://localhost:5173",   # optional for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Pydantic models (request bodies)
# -----------------------------

class EquityRequest(BaseModel):
    hero: str
    villain: str = "random"
    board: Union[str, List[str]] = ""
    trials: int = 500

class EquityResponse(BaseModel):
    hero_win: float
    villain_win: float
    tie: float

class RangeEquityRequest(BaseModel):
    hero_range: str
    villain_range: str
    board: str = ""
    trials: int = 500

class HeatmapRequest(BaseModel):
    hero_range: str
    villain_range: str
    board: str = ""
    trials: int = 500

class PlaySessionRequest(BaseModel):
    id: int = 0
    sessionName: str = ""
    startTime: str = ""
    endTime: str = "datetime.now()"
    stakes: str = "N/A"
    profit: float = 0.0

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

# -----------------------------
# Card Validation
# -----------------------------

def validate_card(card: str):
    if len(card) != 2:
        raise HTTPException(400, f"Invalid card length: '{card}'")

    r, s = card[0], card[1]

    if r not in VALID_RANKS:
        raise HTTPException(400, f"Invalid rank '{r}' in card '{card}'")

    if s not in VALID_SUITS:
        raise HTTPException(400, f"Invalid suit '{s}' in card '{card}'")


# -----------------------------
# Hand Parsing
# -----------------------------
def parse_hand(hand_str: str):
    hand_str = hand_str.strip()

    if len(hand_str) % 2 != 0:
        raise HTTPException(400, f"Hand string has odd length: '{hand_str}'")

    cards = [hand_str[i:i+2] for i in range(0, len(hand_str), 2)]

    for c in cards:
        validate_card(c)

    if len(cards) != 2:
        raise HTTPException(400, f"Hand must contain exactly 2 cards: '{hand_str}'")

    return cards


# -----------------------------
# Board Parsing
# -----------------------------
def parse_board(board):
    if board == "" or board is None:
        return []

    # string board like "AhKdQs"
    if isinstance(board, str):
        board = board.strip()
        if len(board) % 2 != 0:
            raise HTTPException(400, f"Board string has odd length: '{board}'")

        cards = [board[i:i+2] for i in range(0, len(board), 2)]
    else:
        cards = board

    for c in cards:
        validate_card(c)

    if len(cards) not in (0, 3, 4, 5):
        raise HTTPException(400, f"Board must have 0, 3, 4, or 5 cards, got {len(cards)}")

    return cards


# -----------------------------
# Villain Parsing
# -----------------------------
def parse_villain(v: str):
    if v.lower() == "random":
        return None

    return parse_hand(v)


# -----------------------------
# Duplicate Card Detection
# -----------------------------
def check_duplicates(hero, villain, board):
    seen = set()

    for c in hero:
        if c in seen:
            raise HTTPException(400, f"Duplicate card detected: '{c}'")
        seen.add(c)

    if villain:
        for c in villain:
            if c in seen:
                raise HTTPException(400, f"Duplicate card detected: '{c}'")
            seen.add(c)

    for c in board:
        if c in seen:
            raise HTTPException(400, f"Duplicate card detected: '{c}'")
        seen.add(c)


# -----------------------------
# ENDPOINTS - TRAINER
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/equity", response_model=EquityResponse)
def compute_equity(req: EquityRequest):
    # Parse inputs
    hero = parse_hand(req.hero)
    villain = parse_villain(req.villain)
    board = parse_board(req.board)

    # Validate duplicates
    check_duplicates(hero, villain, board)

    # Run simulation
    result = monte_carlo_equity(hero, villain, board, req.trials)

    # Ensure result is a dict
    if not isinstance(result, dict):
        raise HTTPException(500, "Internal error: monte_carlo_equity returned invalid format")

    return {
        "hero_win": result["hero_win"],
        "villain_win": result["villain_win"],
        "tie": result["tie"]
    }
@app.post("/hand_equity")
def hand_equity(payload: dict):
    hero = payload.get("hero")
    villain = payload.get("villain", "random")
    board = payload.get("board", "")
    trials = payload.get("trials", 500)

    if not hero:
        return {"error": "hero hand required"}

        # hero must be canonical 4-char combo (e.g. "AsKd")
    if len(hero) != 4:
        return {"error": "hero must be a 4-character combo like 'AsKd'"}

    result = hand_vs_range_equity(
        hero_combo=hero,
        villain_range=villain,
        board=board,
        trials=trials
    )
    return result

@app.post("/range_equity")
def range_equity(req: RangeEquityRequest):
    return range_vs_range_equity(
        hero_range_str=req.hero_range,
        villain_range_str=req.villain_range,
        board_str=req.board,
        trials=req.trials
    )

def normalize_range(r):
    # If already a list, convert back to string
    if isinstance(r, list):
        return ",".join(r)

    # Single hand like "AKo", "JJ", "A5s"
    if len(r) in (2, 3):
        return r

    # Already a valid range string
    return r

@app.post("/heatmap")
def heatmap(req: HeatmapRequest):
    hero_range = normalize_range(req.hero_range)
    villain_range = normalize_range(req.villain_range)
    board = req.board
    trials = max(10, min(req.trials, 50))  # clamp trials for Render

    # PRE-PARSE villain range ONCE
    villain_classes = expand_range(villain_range)
    villain_combos_all = []
    for vc in villain_classes:
        villain_combos_all.extend(parse_range(vc))
    villain_combos_all = list(set(villain_combos_all))

    # PRE-PARSE board ONCE
    used_cards = [board[i:i+2] for i in range(0, len(board), 2)]

    # FILTER villain combos ONCE
    villain_combos_all = filter_blocked(villain_combos_all, used_cards)

    results = {}

    for hand in ALL_169_HANDS:
        # PRE-PARSE hero hand ONCE
        hero_classes = expand_range(hand)
        hero_combos = []
        for hc in hero_classes:
            hero_combos.extend(parse_range(hc))

        hero_combos = filter_blocked(hero_combos, used_cards)

        # Compute equity using optimized function
        equity = range_vs_range_equity(
            hero_combos,              # pass combos directly
            villain_combos_all,       # pass combos directly
            board,
            trials
        )

        hero_equity = equity["hero_win"] + equity["tie"] / 2
        results[hand] = hero_equity

    return results

# -----------------------------
# ENDPOINTS - BANKROLL
# -----------------------------
DATA_PATH = "data/sessions.json"

def load_sessions():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def save_sessions(sessions):
    with open(DATA_PATH, "w") as f:
        json.dump(sessions, f, indent=2)

@app.get("/load_sessions")
def load_sessions_list():
    return load_sessions()

@app.post("/add_session")
def add_session(req: PlaySessionRequest):
    allSessions = load_sessions()
    new_session = {
        "id": len(allSessions) + 1,
        "sessionName": req.sessionName,
        "startTime": req.startTime,
        "endTime": req.endTime,
        "stakes": req.stakes,
        "profit": req.profit
    }
    print(new_session)

    allSessions.insert(0, new_session)
    save_sessions(allSessions)

    return allSessions

#---------------------------
# ENDPOINTS - DEBUG
#---------------------------

@app.get("/default_equities")
def default_equities():
    filename = os.path.join(CACHE_DIR, "random.csv")
    cache = load_cache(filename)
    print(cache)
    results = {}
    for hand in cache:
        equity = cache[hand]
        hero_equity = equity[0] + (equity[2] / 2)
        print(hand, hero_equity)
        results[hand] = hero_equity
    return results

@app.get("/debug_range")
def debug_range(r: str):
    from .range_parser import parse_range
    combos = parse_range(r)
    return {
        "range": r,
        "count": len(combos),
        "combos": combos
    }

@app.get("/debug_heatmap")
def debug_heatmap(trials: int = 5):
    # Full villain combos
    all_villain = all_2card_combos()

    # Reduce villain sample size drastically
    SAMPLE_SIZE = 20

    results = {}

    for hand in ALL_169_HANDS:

        # Expand hero combos
        hero_classes = expand_range(hand)
        hero_combos = []
        for hc in hero_classes:
            hero_combos.extend(parse_range(hc))

        # Filter villain combos that don't block hero
        villain_combos = [
            v for v in all_villain
            if not blocked(hero_combos[0], v)
        ]

        # SAMPLE villain combos (critical)
        if len(villain_combos) > SAMPLE_SIZE:
            villain_combos = random.sample(villain_combos, SAMPLE_SIZE)

        # Compute equity
        equity = range_vs_range_equity(
            hero_combos,
            villain_combos,
            "",
            trials
        )

        hero_equity = equity["hero_win"] + equity["tie"] / 2
        results[hand] = hero_equity

    return results