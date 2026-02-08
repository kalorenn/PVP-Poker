import pytest
from unittest.mock import MagicMock, patch
from src.bot_logic import get_bot_move

class MockCard:
    def __init__(self, value):
        self.value = value

@pytest.fixture
def setup_game():
    """Creates a basic mock game state and bot player."""
    game_state = MagicMock()
    bot_player = MagicMock()
    
    # Default settings
    game_state.current_bet = 20
    game_state.big_blind = 20
    game_state.community_cards = []
    
    bot_player.current_bet = 0
    bot_player.hand = []
    
    return game_state, bot_player

def test_preflop_pocket_pair_facing_bet(setup_game):
    """Score 1 (Pair) + Cost > 0 -> Call"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(10), MockCard(10)]
    game_state.current_bet = 20
    bot.current_bet = 0
    
    action, amount = get_bot_move(game_state, bot)
    
    assert action == "call"
    assert amount == 0

def test_preflop_pocket_pair_no_cost_aggressive(setup_game):
    """Score 1 (Pair) + Cost 0 + Random > 0.5 -> Raise"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(10), MockCard(10)]
    game_state.current_bet = 20
    bot.current_bet = 20 
    
    with patch('src.bot_logic.random.random', return_value=0.6):
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "raise"
    assert amount == 40

def test_preflop_pocket_pair_no_cost_passive(setup_game):
    """Score 1 (Pair) + Cost 0 + Random <= 0.5 -> Check"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(5), MockCard(5)]
    game_state.current_bet = 20
    bot.current_bet = 20
    
    with patch('src.bot_logic.random.random', return_value=0.4):
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "check"
    assert amount == 0

def test_preflop_high_card_cheap_call(setup_game):
    """Score 0.5 (High Card) + Cost <= BB -> Call"""
    game_state, bot = setup_game

    bot.hand = [MockCard(14), MockCard(5)]

    game_state.current_bet = 20
    bot.current_bet = 0
    game_state.big_blind = 20
    
    action, amount = get_bot_move(game_state, bot)
    
    assert action == "call"

def test_preflop_high_card_expensive_fold(setup_game):
    """Score 0.5 (High Card) + Cost > BB -> Fold"""
    game_state, bot = setup_game

    bot.hand = [MockCard(13), MockCard(2)]

    game_state.current_bet = 100
    bot.current_bet = 0
    game_state.big_blind = 20
    
    action, amount = get_bot_move(game_state, bot)
    
    assert action == "fold"

def test_preflop_weak_hand_check(setup_game):
    """Score 0 (Weak) + Cost 0 -> Check"""
    game_state, bot = setup_game

    bot.hand = [MockCard(2), MockCard(7)]

    game_state.current_bet = 20
    bot.current_bet = 20
    
    action, amount = get_bot_move(game_state, bot)
    
    assert action == "check"

def test_preflop_weak_hand_bluff(setup_game):
    """Score 0 (Weak) + Cost > 0 + Random < 0.1 -> Raise (Bluff)"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(2), MockCard(3)]
    game_state.current_bet = 50
    bot.current_bet = 0

    with patch('src.bot_logic.random.random', return_value=0.05):
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "raise"
    assert amount == 50 + 20 # Current + BB

def test_preflop_weak_hand_fold(setup_game):
    """Score 0 (Weak) + Cost > 0 + Random >= 0.1 -> Fold"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(2), MockCard(3)]
    game_state.current_bet = 50
    bot.current_bet = 0

    with patch('src.bot_logic.random.random', return_value=0.5):
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "fold"
    assert amount == 0

def test_postflop_strong_hand_call(setup_game):
    """Postflop: Score >= 1 + Cost > 0 -> Call"""
    game_state, bot = setup_game

    bot.hand = [MockCard(10), MockCard(10)]
    game_state.community_cards = [MockCard(2), MockCard(3), MockCard(4)]

    with patch('src.bot_logic.HandEvaluator.evaluate', return_value=(2, 'Two Pair')):
        # Facing bet
        game_state.current_bet = 100
        bot.current_bet = 50
        
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "call"

def test_postflop_strong_hand_raise(setup_game):
    """Postflop: Score >= 1 + Cost 0 + Aggressive -> Raise"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(14), MockCard(14)]
    game_state.community_cards = [MockCard(2), MockCard(2), MockCard(5)]
    game_state.current_bet = 0
    bot.current_bet = 0
    
    with patch('src.bot_logic.HandEvaluator.evaluate', return_value=(3, 'Trips')):
        with patch('src.bot_logic.random.random', return_value=0.9):
            action, amount = get_bot_move(game_state, bot)
            
    assert action == "raise"

def test_postflop_weak_hand_check(setup_game):
    """Postflop: Score < 0.5 + Cost 0 -> Check"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(2), MockCard(3)]
    game_state.community_cards = [MockCard(8), MockCard(9), MockCard(10)]
    
    # Evaluator returns 0 (High Card)
    with patch('src.bot_logic.HandEvaluator.evaluate', return_value=(0, 'High Card')):
        game_state.current_bet = 0
        bot.current_bet = 0
        
        action, amount = get_bot_move(game_state, bot)
        
    assert action == "check"

def test_postflop_weak_hand_fold(setup_game):
    """Postflop: Score < 0.5 + Cost > 0 -> Fold"""
    game_state, bot = setup_game
    
    bot.hand = [MockCard(2), MockCard(3)]
    game_state.community_cards = [MockCard(8), MockCard(9), MockCard(10)]
    
    with patch('src.bot_logic.HandEvaluator.evaluate', return_value=(0, 'High Card')):
        game_state.current_bet = 500
        bot.current_bet = 0

        with patch('src.bot_logic.random.random', return_value=0.5):
            action, amount = get_bot_move(game_state, bot)
            
    assert action == "fold"