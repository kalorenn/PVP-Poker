"""
something
"""

from src.database import DatabaseManager
from src.ui import PokerUI

def main():
    """Main function that loads the ui and game"""

    db = DatabaseManager("poker_game.db")
    ui = PokerUI(db)
    ui.run()

if __name__ == "__main__":
    main()
