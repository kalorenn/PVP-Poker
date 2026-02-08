"""
Tests for the PokerUI class.
Includes mocking for pygame and game engine dependencies.
"""
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

mock_pygame = MagicMock()

class MockRect:
    """
    Simulates pygame.Rect for testing.
    """
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.width, self.height = w, h
        self.center = (x + w // 2, y + h // 2)

    def collidepoint(self, pos):
        """Checks if a point is inside the rect."""
        px, py = pos
        return (self.x <= px <= self.x + self.w) and (self.y <= py <= self.y + self.h)

    def move(self, dx, dy):
        """Returns a new moved rect."""
        return MockRect(self.x + dx, self.y + dy, self.w, self.h)

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __getitem__(self, i):
        return [self.x, self.y, self.w, self.h][i]

class MockSurface:
    """Simulates pygame.Surface."""
    def get_rect(self, **_kwargs):
        """Returns a MockRect."""
        return MockRect(0, 0, 100, 50)

    def set_alpha(self, _a):
        """Mock method."""

    def fill(self, _c):
        """Mock method."""

    def blit(self, _source, _dest, _area=None, _special_flags=0):
        """Mock method."""

class MockFont:
    """Simulates pygame.font.Font."""
    def render(self, _text, _antialias, _color):
        """Returns a MockSurface."""
        return MockSurface()

    def size(self, _text):
        """Returns a tuple size."""
        return (100, 20)

mock_pygame.Rect = MockRect
mock_pygame.font.SysFont.side_effect = lambda *args, **kwargs: MockFont()
mock_pygame.Surface.side_effect = lambda *args, **kwargs: MockSurface()
mock_pygame.display.set_mode.return_value = MockSurface()
mock_pygame.time.Clock.return_value = MagicMock()
mock_pygame.time.get_ticks.return_value = 0
mock_pygame.mouse.get_pos.return_value = (0, 0)

patcher = patch.dict('sys.modules', {'pygame': mock_pygame})
patcher.start()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui import PokerUI

@pytest.fixture
def mock_db():
    """Fixture for a mocked database manager."""
    db = MagicMock()
    db.get_leaderboard.return_value = [("Ace", 5000, 10, 1), ("King", 2000, 5, 2)]
    db.get_or_create_player.return_value = (1, 1000)
    return db

@pytest.fixture
def ui(mock_db):
    """Fixture for the PokerUI instance."""
    app = PokerUI(mock_db)
    app.screen = MagicMock()
    app.ui_state = "LOGIN"
    app.game = None
    return app

@pytest.fixture
def mock_game():
    """Fixture for a mocked PokerGame instance."""
    game = MagicMock()
    game.players = []
    game.community_cards = []
    game.pot = 100
    game.current_bet = 20
    game.big_blind = 20
    game.dealer_index = 0
    game.active_player_index = 0
    game.stage = "PREFLOP"
    game.winner = None
    game.mode = "PVE"
    return game

def test_init_defaults(ui):
    """Test initial state of the UI."""
    assert ui.ui_state == "LOGIN"
    assert ui.config['mode'] == 'PVE'
    assert ui.p1_name == ""
    assert len(ui.input_rects) == 2

def test_login_typing_p1(ui):
    """Test typing in the login fields."""
    ui.active_input_idx = 0
    event = MagicMock()
    event.key = 97
    event.unicode = 'A'
    ui._handle_login_typing(event)
    assert ui.p1_name == "A"

    event.key = mock_pygame.K_BACKSPACE
    ui._handle_login_typing(event)
    assert ui.p1_name == ""

def test_login_typing_limit(ui):
    """Test that typing does not exceed character limit."""
    ui.active_input_idx = 0
    ui.p1_name = "A" * 12
    event = MagicMock()
    event.key = 98
    event.unicode = 'B'
    ui._handle_login_typing(event)
    assert len(ui.p1_name) == 12

def test_handle_login_clicks_start_pve(ui):
    """Test clicking the Start PVE button."""
    ui.buttons = [(MockRect(302, 500, 200, 60), "start_pve", 0)]
    with patch('src.ui.PokerGame') as mock_game_class:
        ui._handle_login_clicks((350, 510))
        assert ui.ui_state == "MENU"
        assert ui.game is not None
        assert ui.config['mode'] == "PVE"
        mock_game_class.assert_called_once()

def test_handle_login_clicks_start_pvp_error(ui):
    """Test error handling when PVP names are identical."""
    ui.p1_name = "Player"
    ui.p2_name = "Player"
    ui.buttons = [(MockRect(522, 500, 200, 60), "start_pvp", 0)]
    ui._handle_login_clicks((550, 510))
    assert ui.ui_state == "LOGIN"
    assert ui.message == "Names must be different!"

def test_options_navigation(ui):
    """Test navigation logic for the Options menu."""
    ui.buttons = [(MockRect(302, 580, 200, 50), "show_options", 0)]
    ui._handle_login_clicks((350, 590))
    assert ui.ui_state == "OPTIONS"

    ui.buttons = [(MockRect(50, 50, 100, 50), "back_login", 0)]
    ui._handle_options_clicks((60, 60))
    assert ui.ui_state == "LOGIN"

def test_options_toggles(ui):
    """Test toggling settings in Options."""
    ui.ui_state = "OPTIONS"
    initial_bots = ui.config['bot_count']
    ui.buttons = [(MockRect(720, 200, 40, 30), "toggle_setting", ('bot_count', 1))]
    ui._handle_options_clicks((730, 210))
    assert ui.config['bot_count'] == initial_bots + 1

def test_menu_deal_hand(ui, mock_game):
    """Test the Deal Hand button functionality."""
    ui.ui_state = "MENU"
    ui.game = mock_game
    ui.game.mode = "PVE"
    ui.buttons = [(MockRect(412, 434, 200, 60), "deal_hand", 0)]
    ui._handle_game_general_clicks((450, 450))
    assert ui.ui_state == "GAME"
    ui.game.start_new_hand.assert_called_once()

def test_bot_auto_move_timer(ui, mock_game):
    """Test that bots only move after the delay timer expires."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    bot_player = MagicMock()
    bot_player.is_bot = True
    ui.game.players = [MagicMock(), bot_player]
    ui.game.active_player_index = 1

    mock_pygame.time.get_ticks.return_value = 500
    ui.last_bot_move_time = 0
    ui._update_game_logic()
    ui.game.process_bot_turn.assert_not_called()

    mock_pygame.time.get_ticks.return_value = 1500
    ui._update_game_logic()
    ui.game.process_bot_turn.assert_called_once()

def test_gameplay_buttons_check(ui, mock_game):
    """Test clicking the Check button."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    ui.game.process_action.return_value = "OK"
    ui.buttons = [(MockRect(800, 500, 150, 60), "check", 0)]
    ui._handle_gameplay_clicks((810, 510))
    ui.game.process_action.assert_called_with("check", 0)

def test_raise_menu_logic(ui, mock_game):
    """Test the logic for opening, setting, and confirming raises."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    player = MagicMock()
    player.balance = 1000
    player.current_bet = 0
    ui.game.players = [player]
    ui.game.current_bet = 20
    ui.game.big_blind = 20
    ui.game.pot = 100

    ui.buttons = [(MockRect(0, 0, 10, 10), "open_raise_menu", 0)]
    ui._handle_gameplay_clicks((5, 5))
    assert ui.show_raise_menu is True

    ui.buttons = [(MockRect(10, 10, 10, 10), "set_raise", 1.0)]
    ui._handle_gameplay_clicks((15, 15))
    assert ui.raise_amount == 140

    ui.buttons = [(MockRect(20, 20, 10, 10), "raise", 140)]
    ui.game.process_action.return_value = "OK"
    ui._handle_gameplay_clicks((25, 25))
    assert ui.show_raise_menu is False
    ui.game.process_action.assert_called_with("raise", 140)

def test_slider_drag_logic(ui, mock_game):
    """Test dragging the raise slider."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    ui.show_raise_menu = True
    player = MagicMock()
    player.balance = 1000
    player.current_bet = 0
    ui.game.players = [player]
    ui.game.current_bet = 20
    ui.game.big_blind = 20
    ui.slider_rect = MockRect(312, 608, 400, 10)
    mouse_x = 312 + 200
    ui._update_slider(mouse_x)
    assert 500 <= ui.raise_amount <= 540

def test_game_over_state(ui, mock_game):
    """Test transition to Game Over state on showdown."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    ui.game.stage = "SHOWDOWN"
    ui._handle_gameplay_clicks((0, 0))
    assert ui.ui_state == "GAMEOVER"

def test_leave_table(ui, mock_game):
    """Test leaving the table."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    p1 = MagicMock()
    p1.id = 99
    ui.game.players = [p1]
    ui.buttons = [(MockRect(0, 0, 10, 10), "leave_table", 0)]
    ui._handle_game_general_clicks((5, 5))
    assert ui.game is None
    assert ui.ui_state == "LOGIN"
    mock_game.leave_game.assert_called_with(99)

def test_draw_login(ui):
    """Test drawing the login screen."""
    ui.ui_state = "LOGIN"
    ui.input_rects = [MockRect(0, 0, 10, 10), MockRect(0, 0, 10, 10)]
    ui.draw()

def test_draw_game(ui, mock_game):
    """Test drawing the main game screen."""
    ui.ui_state = "GAME"
    ui.game = mock_game
    p1 = MagicMock()
    p1.name = "Hero"
    p1.balance = 1000
    p1.current_bet = 0
    p1.is_all_in = False
    p1.hand = [MagicMock(rank='A', suit='H')]
    p2 = MagicMock()
    p2.name = "Villain"
    p2.balance = 2000
    p2.current_bet = 0
    p2.is_all_in = False
    p2.hand = [MagicMock(rank='K', suit='D')]
    ui.game.players = [p1, p2]
    ui.game.community_cards = [MagicMock(rank='10', suit='S')]
    ui.draw()

def test_draw_raise_menu(ui, mock_game):
    """Test drawing the raise menu."""
    ui.ui_state = "GAME"
    ui.show_raise_menu = True
    ui.game = mock_game
    player = MagicMock()
    player.balance = 1000
    player.current_bet = 0
    ui.game.players = [player]
    ui.game.current_bet = 20
    ui.game.big_blind = 20
    ui.draw()
