"""
The implementation of the elements and logic of the
rules of Texas Hold'Em poker
"""

import random
import itertools
from dataclasses import dataclass, field
from typing import List, Tuple
from collections import Counter

RANK_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}
SUITS = ['H', 'D', 'C', 'S']

@dataclass(order=True, frozen=True)
class Card:
    """Represents a standard playing card."""
    value: int = field(init=False)
    rank: str
    suit: str

    def __post_init__(self):
        object.__setattr__(self, 'value', RANK_VALUES[self.rank])

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

class Deck:
    """Represents a 52 card deck."""
    def __init__(self) -> None:
        self.cards: List[Card] = []
        self._initialize_deck()

    def _initialize_deck(self) -> None:
        """Populates the deck with 52 cards."""
        self.cards = [
            Card(rank=r, suit=s)
            for r in RANK_VALUES
            for s in SUITS
        ]

    def shuffle(self) -> None:
        """Shuffles the deck in place."""
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> List[Card]:
        """Deals 'count' cards from the top of the deck."""
        if len(self.cards) < count:
            raise ValueError("Not enough cards in deck to deal.")

        dealt_cards = []
        for _ in range(count):
            dealt_cards.append(self.cards.pop())
        return dealt_cards

    def __len__(self) -> int:
        return len(self.cards)

class HandEvaluator:
    """
    Evaluates the strength of a poker hand.
    Input: 7 cards (2 hole + 5 community).
    Output: Best 5-card hand score.
    """

    # Hand Rankings
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9

    @staticmethod
    def evaluate(cards: List[Card]) -> Tuple[int, List[int]]:
        """
        Determines the best 5-card hand from a list of cards (usually 7).
        Returns a tuple: (Hand_Category_Score, List_of_Tie_Breakers)
        """
        if len(cards) < 5:
            raise ValueError("Need at least 5 cards to evaluate.")

        # here generate all 5 card combinations
        possible_hands = itertools.combinations(cards, 5)
        best_score: Tuple[int, List[int]] = (-1, [])

        for hand in possible_hands:
            score = HandEvaluator._score_five_cards(list(hand))
            best_score = max(best_score, score)

        return best_score

    @staticmethod
    def _score_five_cards(cards: List[Card]) -> Tuple[int, List[int]]:
        """Internal method to score exactly 5 cards."""
        cards.sort(key=lambda c: c.value, reverse=True)
        values = [c.value for c in cards]
        suits = [c.suit for c in cards]

        is_flush = len(set(suits)) == 1

        is_straight = False
        if len(set(values)) == 5 and (values[0] - values[4] == 4):
            is_straight = True
        if values == [14, 5, 4, 3, 2]:
            is_straight = True
            values = [5, 4, 3, 2, 1]

        if is_straight and is_flush:
            if values[0] == 14: # Royal
                return (HandEvaluator.ROYAL_FLUSH, values)
            return (HandEvaluator.STRAIGHT_FLUSH, values)

        counts = Counter(values)
        count_values = counts.most_common()


        if count_values[0][1] == 4:
            return (HandEvaluator.FOUR_OF_A_KIND, [count_values[0][0], count_values[1][0]])

        if count_values[0][1] == 3 and count_values[1][1] == 2:
            return (HandEvaluator.FULL_HOUSE, [count_values[0][0], count_values[1][0]])

        if is_flush:
            return (HandEvaluator.FLUSH, values)

        if is_straight:
            return (HandEvaluator.STRAIGHT, values)

        if count_values[0][1] == 3:
            kickers = sorted([k for k, v in counts.items() if v == 1], reverse=True)
            return (HandEvaluator.THREE_OF_A_KIND, [count_values[0][0]] + kickers)

        if count_values[0][1] == 2 and count_values[1][1] == 2:
            pairs = sorted([k for k, v in counts.items() if v == 2], reverse=True)
            kicker = [k for k, v in counts.items() if v == 1][0]
            return (HandEvaluator.TWO_PAIR, pairs + [kicker])

        if count_values[0][1] == 2:
            kickers = sorted([k for k, v in counts.items() if v == 1], reverse=True)
            return (HandEvaluator.PAIR, [count_values[0][0]] + kickers)

        return (HandEvaluator.HIGH_CARD, values)
