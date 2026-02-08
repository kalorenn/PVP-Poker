import pytest
from src.player import Player
from src.game_logic import Card

def create_card(rank='A', suit='H'):
    """Helper to create a Card object for testing."""

    return Card(rank=rank, suit=suit)


def test_player_initialization():
    """Test that a player is initialized with correct default values."""
    p = Player(id=1, name="TestPlayer", balance=1000)
    
    assert p.id == 1
    assert p.name == "TestPlayer"
    assert p.balance == 1000
    assert p.is_bot is False
    assert p.hand == []
    assert p.current_bet == 0
    assert p.is_folded is False
    assert p.is_all_in is False

def test_player_bot_flag():
    """Test initializing a player as a bot."""
    p = Player(id=2, name="Bot1", balance=500, is_bot=True)
    assert p.is_bot is True

def test_add_card():
    """Test adding cards to the player's hand."""
    p = Player(id=1, name="Player", balance=1000)
    c1 = create_card('A', 'S')
    c2 = create_card('K', 'D')
    
    p.add_card(c1)
    assert len(p.hand) == 1
    assert p.hand[0] == c1
    
    p.add_card(c2)
    assert len(p.hand) == 2
    assert p.hand[1] == c2

def test_place_bet_normal():
    """Test placing a bet within balance limits."""
    p = Player(id=1, name="Player", balance=1000)
    
    bet_amount = p.place_bet(100)
    
    assert bet_amount == 100
    assert p.balance == 900
    assert p.current_bet == 100
    assert p.is_all_in is False

def test_place_bet_cumulative():
    """Test that multiple bets accumulate correctly in current_bet."""
    p = Player(id=1, name="Player", balance=1000)
    
    p.place_bet(100)
    p.place_bet(50)
    
    assert p.balance == 850
    assert p.current_bet == 150

def test_place_bet_all_in_exact():
    """Test betting exactly the entire balance."""
    p = Player(id=1, name="Player", balance=500)
    
    bet_amount = p.place_bet(500)
    
    assert bet_amount == 500
    assert p.balance == 0
    assert p.current_bet == 500

    assert p.is_all_in is False 

def test_place_bet_all_in_exceed():
    """Test betting more than balance triggers All-In state."""
    p = Player(id=1, name="Player", balance=500)

    bet_amount = p.place_bet(600)

    assert bet_amount == 500
    assert p.balance == 0
    assert p.current_bet == 500
    assert p.is_all_in is True

def test_reset_for_new_round():
    """Test that resetting the player clears hand and round status."""
    p = Player(id=1, name="Player", balance=1000)

    p.add_card(create_card('10', 'H'))
    p.place_bet(100)
    p.is_folded = True
    p.is_all_in = True

    p.reset_for_new_round()

    assert p.hand == []
    assert p.current_bet == 0
    assert p.is_folded is False
    assert p.is_all_in is False
    assert p.balance == 900

def test_actions_dict_initialization():
    """Test that the actions dictionary is initialized correctly."""
    p = Player(id=1, name="Player", balance=1000)
    
    assert isinstance(p.actions, dict)
    assert p.actions['fold'] == 0
    assert p.actions['raise'] == 0

def test_last_action_text_default():
    """Test default empty action text."""
    p = Player(id=1, name="Player", balance=1000)
    assert p.last_action_text == ""
