"""
something
"""

from typing import List
from dataclasses import dataclass, field
from .game_logic import Card

@dataclass
class Player:
    id: int
    name: str
    balance: int
    is_bot: bool = False  # <--- NEW FIELD

    last_action_text: str = ""
    
    hand: List[Card] = field(default_factory=list)
    current_bet: int = 0
    is_folded: bool = False
    is_all_in: bool = False
    actions: dict = field(default_factory=lambda: {'fold': 0, 'check': 0, 'bet': 0, 'raise': 0})

    def reset_for_new_round(self):
        self.hand = []
        self.current_bet = 0
        self.is_folded = False
        self.is_all_in = False
    
    def add_card(self, card: Card):
        self.hand.append(card)

    def place_bet(self, amount: int) -> int:
        if amount > self.balance:
            amount = self.balance
            self.is_all_in = True
        self.balance -= amount
        self.current_bet += amount
        return amount