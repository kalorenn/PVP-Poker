import pytest
import sqlite3
import os
from src.database import DatabaseManager

@pytest.fixture
def db(tmp_path):
    """
    Creates a DatabaseManager instance using a temporary file.
    This persists data across connections (unlike :memory:) but is 
    still isolated and cleaned up by pytest after testing.
    """

    db_file = tmp_path / "test_poker_stats.db"
    return DatabaseManager(str(db_file))

def test_tables_created_on_init(db):
    """Test that necessary tables are created upon initialization."""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
    
    assert "players" in tables
    assert "game_history" in tables

def test_get_or_create_new_player(db):
    """Test creating a brand new player returns default values."""
    pid, balance = db.get_or_create_player("new_user")
    
    assert pid is not None
    assert isinstance(pid, int)
    assert balance == 1000

def test_get_or_create_existing_player(db):
    """Test that retrieving an existing player returns current data, not defaults."""

    pid1, _ = db.get_or_create_player("existing_user")

    db.update_balance(pid1, 500)
    
    # 3. Retrieve again
    pid2, balance = db.get_or_create_player("existing_user")
    
    assert pid1 == pid2
    assert balance == 1500

def test_update_balance(db):
    """Test adding and subtracting from player balance."""
    pid, _ = db.get_or_create_player("money_maker")

    db.update_balance(pid, 200)
    _, bal = db.get_or_create_player("money_maker")
    assert bal == 1200

    db.update_balance(pid, -1200)
    _, bal = db.get_or_create_player("money_maker")
    assert bal == 0

def test_record_hand_stats_winner(db):
    """Test that winning a hand updates all relevant stats and history."""
    pid, _ = db.get_or_create_player("winner")
    actions = {'bet': 2, 'raise': 1, 'call': 0}
    
    db.record_hand_stats(
        player_id=pid, 
        won=True, 
        pot_size=500, 
        hand_score=8, 
        actions=actions
    )
    
    with db._get_connection() as conn:
        row = conn.execute("""
            SELECT hands_played, hands_won, biggest_pot_won, best_hand_score, bets, raises 
            FROM players WHERE id=?""", (pid,)
        ).fetchone()
        
        assert row[0] == 1
        assert row[1] == 1
        assert row[2] == 500
        assert row[3] == 8
        assert row[4] == 2
        assert row[5] == 1

        hist = conn.execute("SELECT winner_id, pot_size FROM game_history").fetchone()
        assert hist is not None
        assert hist[0] == pid
        assert hist[1] == 500

def test_record_hand_stats_loser(db):
    """Test that losing a hand updates play counts but not win counts."""
    pid, _ = db.get_or_create_player("loser")
    actions = {'fold': 1}
    
    db.record_hand_stats(
        player_id=pid, 
        won=False, 
        pot_size=0, 
        hand_score=2, 
        actions=actions
    )
    
    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT hands_played, hands_won, folds FROM players WHERE id=?", 
            (pid,)
        ).fetchone()
        
        assert row[0] == 1
        assert row[1] == 0
        assert row[2] == 1

def test_leaderboard_sorting(db):
    """Test that leaderboard returns players sorted by balance DESC."""
    p1, _ = db.get_or_create_player("Rich")
    db.update_balance(p1, 9000)
    
    p2, _ = db.get_or_create_player("Middle")
    
    p3, _ = db.get_or_create_player("Poor")
    db.update_balance(p3, -500)
    
    leaders = db.get_leaderboard(limit=10)
    
    assert len(leaders) == 3
    assert leaders[0][0] == "Rich"
    assert leaders[0][1] == 10000
    assert leaders[1][0] == "Middle"
    assert leaders[2][0] == "Poor"

def test_leaderboard_limit(db):
    """Test that the leaderboard respects the limit argument."""
    for i in range(5):
        db.get_or_create_player(f"User{i}")
        
    leaders = db.get_leaderboard(limit=3)
    assert len(leaders) == 3

def test_delete_player(db):
    """Test deleting a player removes them from the database."""
    pid, _ = db.get_or_create_player("temp_user")
    
    db.delete_player(pid)
    
    with db._get_connection() as conn:
        res = conn.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
    
    assert res is None

def test_best_hand_update_logic(db):
    """Test that best_hand_score only updates if the new score is higher."""
    pid, _ = db.get_or_create_player("card_shark")

    db.record_hand_stats(pid, True, 10, 5, {})

    db.record_hand_stats(pid, True, 10, 2, {})

    db.record_hand_stats(pid, True, 10, 8, {})
    
    with db._get_connection() as conn:
        score = conn.execute("SELECT best_hand_score FROM players WHERE id=?", (pid,)).fetchone()[0]
    
    assert score == 8
