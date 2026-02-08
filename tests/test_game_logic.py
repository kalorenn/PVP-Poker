import pytest
from src.game_logic import Card, Deck, HandEvaluator

# --- Helper Function for Readability ---
def cards_from_str(card_str: str):
    """
    Parses a string like 'Ah Kd 10s' into a list of Card objects.
    Ranks: 2-9, 10, J, Q, K, A
    Suits: H, D, C, S
    """
    cards = []
    parts = card_str.split()
    for part in parts:
        suit = part[-1]
        rank = part[:-1]
        cards.append(Card(rank=rank, suit=suit))
    return cards

# --- Card & Deck Tests ---

def test_card_initialization():
    """Test that cards correctly assign integer values to ranks."""
    c1 = Card(rank='A', suit='H')
    assert c1.value == 14
    
    c2 = Card(rank='2', suit='D')
    assert c2.value == 2
    
    c3 = Card(rank='10', suit='C')
    assert c3.value == 10

def test_deck_integrity():
    """Test that a new deck has 52 unique cards."""
    deck = Deck()
    assert len(deck) == 52
    
    # Verify uniqueness
    unique_cards = set(str(c) for c in deck.cards)
    assert len(unique_cards) == 52

def test_deck_deal():
    """Test dealing mechanics."""
    deck = Deck()
    hand = deck.deal(5)
    
    assert len(hand) == 5
    assert len(deck) == 47  # 52 - 5
    
    # Ensure dealt cards are removed
    for card in hand:
        assert card not in deck.cards

def test_deck_empty_error():
    """Test dealing from an empty deck raises an error."""
    deck = Deck()
    deck.deal(52) # Empty the deck
    
    with pytest.raises(ValueError, match="Not enough cards"):
        deck.deal(1)

# --- Hand Evaluator Tests ---

def test_royal_flush():
    """Test identification of a Royal Flush."""
    hand = cards_from_str("Ah Kh Qh Jh 10h 2d 3c") # 7 cards
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.ROYAL_FLUSH

def test_straight_flush():
    """Test identification of a Straight Flush (non-royal)."""
    hand = cards_from_str("9s 8s 7s 6s 5s Ac 2d")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.STRAIGHT_FLUSH
    assert kickers[0] == 9 # High card of the straight

def test_four_of_a_kind():
    """Test identification of Quads."""
    hand = cards_from_str("9s 9h 9d 9c 5s Ac 2d")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.FOUR_OF_A_KIND
    # Kickers should be [Rank of Quad, Kicker] -> [9, 14 (Ace)]
    assert kickers == [9, 14]

def test_full_house():
    """Test identification of a Full House."""
    hand = cards_from_str("Ks Kh Kd Qs Qh 2d 3c")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.FULL_HOUSE
    assert kickers == [13, 12] # Kings over Queens

def test_flush():
    """Test identification of a Flush (non-straight)."""
    hand = cards_from_str("Ah 2h 5h 9h Jh Kd Qc")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.FLUSH
    # Should sort flush cards descending: A, J, 9, 5, 2
    assert kickers == [14, 11, 9, 5, 2]

def test_straight_standard():
    """Test a standard straight."""
    hand = cards_from_str("10s 9h 8d 7c 6s 2h 2d")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.STRAIGHT
    assert kickers[0] == 10

def test_straight_wheel():
    """Test the Ace-low straight (Wheel): A-2-3-4-5."""
    hand = cards_from_str("Ah 2d 3c 4s 5h 9d 9c")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.STRAIGHT
    # Logic in code sets Wheel values to [5, 4, 3, 2, 1] to ensure it loses to 6-high straight
    assert kickers == [5, 4, 3, 2, 1]

def test_three_of_a_kind():
    """Test Three of a Kind."""
    hand = cards_from_str("8s 8h 8d 2c 4s 9h Jd")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.THREE_OF_A_KIND
    # Kickers: [Trip_Rank, Kicker1, Kicker2] -> [8, 11 (Jack), 9]
    assert kickers == [8, 11, 9]

def test_two_pair():
    """Test Two Pair."""
    hand = cards_from_str("Js Jh 4d 4c 9s 2h 3d")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.TWO_PAIR
    # [Pair1, Pair2, Kicker] -> [11, 4, 9]
    assert kickers == [11, 4, 9]

def test_one_pair():
    """Test One Pair."""
    hand = cards_from_str("As Ad 2c 4h 6s 8d 10c")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.PAIR
    # [Pair, Kicker1, Kicker2, Kicker3] -> [14, 10, 8, 6]
    assert kickers == [14, 10, 8, 6]

def test_high_card():
    """Test High Card (garbage hand)."""
    hand = cards_from_str("As Kd 9c 7h 5s 3d 2c")
    score, kickers = HandEvaluator.evaluate(hand)
    
    assert score == HandEvaluator.HIGH_CARD
    # Should select top 5: A, K, 9, 7, 5
    assert kickers == [14, 13, 9, 7, 5]

def test_tie_breaking_flush():
    """Test that a higher flush beats a lower flush."""
    # Flush A high
    hand1 = cards_from_str("Ah Jh 9h 5h 2h") 
    # Flush K high
    hand2 = cards_from_str("Kh Qh Jh 9h 5h")
    
    res1 = HandEvaluator.evaluate(hand1)
    res2 = HandEvaluator.evaluate(hand2)
    
    # Tuple comparison: (5, [14...]) > (5, [13...])
    assert res1 > res2

def test_tie_breaking_kickers():
    """Test that same pair rank is broken by kickers."""
    # Pair of Aces, King Kicker
    hand1 = cards_from_str("As Ad Ks 8h 2d")
    # Pair of Aces, Queen Kicker
    hand2 = cards_from_str("Ac Ah Qs 8d 2c")
    
    res1 = HandEvaluator.evaluate(hand1)
    res2 = HandEvaluator.evaluate(hand2)
    
    assert res1 > res2

def test_best_5_of_7():
    """Test that evaluator picks the best 5 cards from 7 available."""
    # Board has 4 hearts. Player 1 has 1 heart (Flush). Player 2 has 3 of a kind.
    # Actually, let's just check one hand finds the flush over the pair.
    
    # Hand: Pair of 2s, but also 5 hearts.
    hand = cards_from_str("2h 2d 5h 7h 9h Jh 3c")
    
    score, kickers = HandEvaluator.evaluate(hand)
    
    # Should prioritize Flush (score 5) over Pair (score 1)
    assert score == HandEvaluator.FLUSH
