"""
something
"""
import random
from typing import Tuple
from .game_logic import HandEvaluator

def get_bot_move(game_state, bot_player) -> Tuple[str, int]:
    """
    Decides the bot's move based on the game state.
    Returns: (Action_String, Amount)
    """
    # 1. Analyze Context
    current_bet = game_state.current_bet
    call_cost = current_bet - bot_player.current_bet
    all_cards = bot_player.hand + game_state.community_cards

    # 2. Evaluate Hand Strength (Score: 0=HighCard, 1=Pair, ..., 9=RoyalFlush)
    if len(all_cards) >= 5:
        score, _ = HandEvaluator.evaluate(all_cards)
    else:
        # Preflop heuristic: High cards are good
        score = 0
        ranks = [c.value for c in bot_player.hand]
        if len(set(ranks)) < 2:
            score = 1  # Pocket Pair
        elif max(ranks) >= 12:
            score = 0.5  # High Card (Q, K, A)

    # 3. Decision Logic
    action, amount = "fold", 0

    # Case A: Strong Hand (Pair or better)
    if score >= 1:
        if call_cost > 0:
            action, amount = "call", 0
        elif random.random() > 0.5:
            action, amount = "raise", current_bet + game_state.big_blind
        else:
            action, amount = "check", 0

    # Case B: Decent Hand (High Card Preflop)
    elif score == 0.5:
        if call_cost <= game_state.big_blind:
            action, amount = "call", 0

    # Case C: Weak Hand (High Card Postflop or Junk)
    else:
        if call_cost == 0:
            action, amount = "check", 0
        elif random.random() < 0.1:
            action, amount = "raise", current_bet + game_state.big_blind

    return action, amount
