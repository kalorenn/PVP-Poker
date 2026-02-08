"""
something
"""

from src.database import DatabaseManager
from src.ui import PokerUI

def main():
    """something"""
    # 1. Initialize Database
    db = DatabaseManager("poker_game.db")
    # 2. Launch GUI (Pass DB only, Game is None initially)
    # The UI will handle the login and Game creation.
    ui = PokerUI(db)
    ui.run()

if __name__ == "__main__":
    main()
