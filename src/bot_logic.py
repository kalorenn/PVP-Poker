"""
Implementation of the logic and behaviour of the bot players
"""
import random
from typing import Tuple
from .game_logic import HandEvaluator

def get_bot_move(game_state, bot_player) -> Tuple[str, int]:
    """
    Decides the bot's move based on the game state.
    Returns: (Action_String, Amount)
    """
    current_bet = game_state.current_bet
    call_cost = current_bet - bot_player.current_bet
    all_cards = bot_player.hand + game_state.community_cards

    if len(all_cards) >= 5:
        score, _ = HandEvaluator.evaluate(all_cards)
    else:
        score = 0
        ranks = [c.value for c in bot_player.hand]
        if len(set(ranks)) < 2:
            score = 1  # Pocket Pair
        elif max(ranks) >= 12:
            score = 0.5  # High Card (Q, K, A)

    action, amount = "fold", 0

    # strong hand
    if score >= 1:
        if call_cost > 0:
            action, amount = "call", 0
        elif random.random() > 0.5:
            action, amount = "raise", current_bet + game_state.big_blind
        else:
            action, amount = "check", 0

    # ok hand
    elif score == 0.5:
        if call_cost <= game_state.big_blind:
            action, amount = "call", 0

    # weak hand
    else:
        if call_cost == 0:
            action, amount = "check", 0
        elif random.random() < 0.1:
            action, amount = "raise", current_bet + game_state.big_blind

    return action, amount
