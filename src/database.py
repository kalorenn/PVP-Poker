"""
Implementation of the SQLite database of the human player accounts
"""

import sqlite3
from typing import List, Tuple, Any

class DatabaseManager:
    def __init__(self, db_name: str = "poker_stats.db") -> None:
        self.db_name = db_name
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name)

    def _create_tables(self) -> None:
        query_players = """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            balance INTEGER DEFAULT 1000,
            hands_played INTEGER DEFAULT 0,
            hands_won INTEGER DEFAULT 0,
            biggest_pot_won INTEGER DEFAULT 0,
            best_hand_score INTEGER DEFAULT -1,
            folds INTEGER DEFAULT 0,
            checks INTEGER DEFAULT 0,
            bets INTEGER DEFAULT 0,
            raises INTEGER DEFAULT 0
        );
        """
        query_history = """
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            winner_id INTEGER,
            pot_size INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(winner_id) REFERENCES players(id)
        );
        """
        with self._get_connection() as conn:
            conn.execute(query_players)
            conn.execute(query_history)

    def get_or_create_player(self, username: str) -> Tuple[int, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, balance FROM players WHERE username = ?", (username,))
            result = cursor.fetchone()
            if result:
                return result
            cursor.execute("INSERT INTO players (username) VALUES (?)", (username,))
            conn.commit()
            return cursor.lastrowid, 1000

    def update_balance(self, player_id: int, amount: int) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE players SET balance = balance + ? WHERE id = ?", (amount, player_id))

    def record_hand_stats(self, player_id: int, won: bool, pot_size: int, hand_score: int, actions: dict) -> None:
        with self._get_connection() as conn:
            query = """
            UPDATE players SET 
                hands_played = hands_played + 1,
                hands_won = hands_won + ?,
                folds = folds + ?,
                checks = checks + ?,
                bets = bets + ?,
                raises = raises + ?
            WHERE id = ?
            """
            conn.execute(query, (
                1 if won else 0,
                actions.get('fold', 0),
                actions.get('check', 0),
                actions.get('bet', 0),
                actions.get('raise', 0),
                player_id
            ))
            if won:
                conn.execute("UPDATE players SET biggest_pot_won = MAX(biggest_pot_won, ?) WHERE id = ?", (pot_size, player_id))
                conn.execute("INSERT INTO game_history (winner_id, pot_size) VALUES (?, ?)", (player_id, pot_size))
            conn.execute("UPDATE players SET best_hand_score = MAX(best_hand_score, ?) WHERE id = ?", (hand_score, player_id))

    def get_leaderboard(self, limit: int = 10) -> List[Tuple[Any, ...]]:
        """Returns top players ordered by balance. Default limit 10."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, balance, hands_won, id FROM players ORDER BY balance DESC LIMIT ?", 
                (limit,)
            )
            return cursor.fetchall()

    def delete_player(self, player_id: int) -> None:
        """Deletes a player by ID."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
