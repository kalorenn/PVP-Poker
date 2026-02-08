import pytest
from unittest.mock import MagicMock, patch
from src.game_engine import PokerGame, PREFLOP, FLOP, SHOWDOWN

@pytest.fixture
def mock_db():
    """Creates a mock database manager with a working connection context."""
    db = MagicMock()

    mock_conn = MagicMock()
    db._get_connection.return_value.__enter__.return_value = mock_conn

    mock_conn.execute.return_value.fetchone.return_value = ("HumanPlayer", 1000)
    
    return db

@pytest.fixture
def game(mock_db):
    """Initializes a standard 1v1 PVE game for testing."""
    config = {
        'mode': 'PVE',
        'bot_count': 1,
        'small_blind': 10,
        'raise_limit': 0
    }

    g = PokerGame(mock_db, human_id=1, config=config)
    
    g.dealer_index = 1 
    
    return g

def test_initialization(game):
    """Test that the game initializes with correct player counts and balances."""
    assert len(game.players) == 2
    assert game.players[0].name == "HumanPlayer"
    assert game.players[1].is_bot is True
    assert game.small_blind == 10
    assert game.big_blind == 20

def test_start_new_hand_blinds(game):
    """Test that a new hand posts blinds and deals cards."""
    game.start_new_hand()

    assert game.pot == 30
    assert game.current_bet == 20

    assert game.players[0].current_bet == 10
    assert game.players[1].current_bet == 20

    assert len(game.players[0].hand) == 2
    assert len(game.players[1].hand) == 2

    assert game.stage == PREFLOP

def test_illegal_check(game):
    """Test that a player cannot check if they are facing a bet."""
    game.start_new_hand()

    game.active_player_index = 0
    
    result = game.process_action("check")
    assert result == "Cannot check, must call."

def test_successful_call(game):
    """Test that calling matches the current bet."""
    game.start_new_hand()

    game.active_player_index = 0
    initial_balance = game.players[0].balance # 990
    
    result = game.process_action("call")
    
    assert result == "OK"

    assert game.players[0].balance == initial_balance - 10
    assert game.pot == 40

def test_fold_ends_hand(game):
    """Test that folding immediately ends the hand in Heads-Up."""
    game.start_new_hand()
    game.active_player_index = 0
    
    result = game.process_action("fold")
    
    assert result == "Hand Over"
    assert game.players[0].is_folded is True
    # Player 1 should be the winner
    assert game.winner == game.players[1]

def test_raise_logic(game):
    """Test raising logic and minimum raise enforcement."""
    game.start_new_hand()
    game.active_player_index = 0

    result = game.process_action("raise", 30)
    assert result == "Raise too small"

    result = game.process_action("raise", 50)
    assert result == "OK"
    assert game.current_bet == 50
    assert game.pot == 70 

def test_advance_stage_to_flop(game):
    """Test transitioning from Preflop to Flop."""
    game.start_new_hand()

    game.active_player_index = 0
    game.process_action("call")

    game.active_player_index = 1
    game.process_action("check")

    assert game.stage == FLOP
    assert len(game.community_cards) == 3
    assert game.current_bet == 0

def test_showdown_winner_determination(game):
    """Test that the player with the higher score wins the pot."""
    game.start_new_hand()
    game.stage = SHOWDOWN
    game.pot = 100

    with patch('src.game_engine.HandEvaluator') as mock_evaluator:
        mock_evaluator.evaluate.side_effect = [(100, "Flush"), (50, "Pair")]
        
        game._resolve_showdown()
        
        assert game.winner == game.players[0]
        assert game.players[0].balance == 1000 - 10 + 100

def test_bot_turn_execution(game):
    """Test that process_bot_turn calls the bot logic and executes the move."""
    game.start_new_hand()
    game.active_player_index = 1
    
    with patch('src.game_engine.get_bot_move') as mock_bot_logic:
        mock_bot_logic.return_value = ("call", 0)
        
        game.process_bot_turn()
        
        assert game.players[1].last_action_text == "Call"
        mock_bot_logic.assert_called_once()

def test_insufficient_players_game_over(game):
    """Test that game returns GAME_OVER if players are broke."""
    for p in game.players:
        p.balance = 0
        
    result = game.start_new_hand()
    assert result == "GAME_OVER"

def test_leave_game_saves_balance(game, mock_db):
    """Test that leaving the game writes balance to DB."""
    p1 = game.players[0]
    p1.balance = 555
    
    game.leave_game(p1.id)

    mock_conn = mock_db._get_connection.return_value.__enter__.return_value
    args, _ = mock_conn.execute.call_args
    
    assert "UPDATE players SET balance=?" in args[0]
    assert args[1][0] == 555

def test_betting_round_not_over_if_action_needed(game):
    """Test that round doesn't end if players haven't acted, even if bets equal."""
    game.start_new_hand()

    game.active_player_index = 0
    game.process_action("call")

    is_over = game._is_betting_round_over()
    assert is_over is False