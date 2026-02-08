"""
The main game engine. Has One versus One and Solo play support
"""

from typing import List, Tuple, Optional, Dict
from .game_logic import Deck, Card, HandEvaluator
from .player import Player
from .database import DatabaseManager
from .bot_logic import get_bot_move

# Constants
PREFLOP = "PREFLOP"
FLOP = "FLOP"
TURN = "TURN"
RIVER = "RIVER"
SHOWDOWN = "SHOWDOWN"

class PokerGame:
    def __init__(self, db: DatabaseManager, human_id: int, config: Dict):
        """
        config: {'mode': 'PVE', 'bot_count': 3, 'small_blind': 10, 'raise_limit': 0}
        """
        self.db = db
        self.config = config
        self.mode = config.get('mode', 'PVE')
        
        self.players: List[Player] = []

        # human setup
        p1_data = self._get_player_data(human_id)
        self.players.append(Player(id=human_id, name=p1_data[0], balance=p1_data[1]))

        # bot setup
        if self.mode == 'PVP':
            p2_id = config.get('p2_id', 0)
            if p2_id:
                p2_data = self._get_player_data(p2_id)
                self.players.append(Player(id=p2_id, name=p2_data[0], balance=p2_data[1]))
        else:
            bot_count = config.get('bot_count', 1)
            for i in range(bot_count):
                self.players.append(Player(
                    id=9000+i, 
                    name=f"Bot {i+1}", 
                    balance=2000, 
                    is_bot=True
                ))

        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.stage = PREFLOP

        self.dealer_index = 0
        self.active_player_index = 0
        self.actions_this_round = 0

        self.small_blind = config.get('small_blind', 10)
        self.big_blind = self.small_blind * 2

        self.winner: Optional[Player] = None

    def _get_player_data(self, pid: int):
        with self.db._get_connection() as conn:
            return conn.execute("SELECT username, balance FROM players WHERE id=?", (pid,)).fetchone()

    def start_new_hand(self):
        self.deck = Deck()
        self.deck.shuffle()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.winner = None
        self.stage = PREFLOP
        self.actions_this_round = 0

        self.dealer_index = (self.dealer_index + 1) % len(self.players)

        active_count = 0
        for p in self.players:
            p.reset_for_new_round()
            if p.balance > 0: active_count += 1
            
        if active_count < 2:
            return "GAME_OVER"

        for _ in range(2):
            for p in self.players:
                if p.balance > 0:
                    p.add_card(self.deck.deal(1)[0])

        n = len(self.players)

        if n == 2:
            sb_idx = self.dealer_index
            bb_idx = (self.dealer_index + 1) % n
        else:
            sb_idx = (self.dealer_index + 1) % n
            bb_idx = (self.dealer_index + 2) % n

        self._post_bet(self.players[sb_idx], self.small_blind)
        self._post_bet(self.players[bb_idx], self.big_blind)

        self.active_player_index = (bb_idx + 1) % n

    def _post_bet(self, player: Player, amount: int):
        actual_bet = player.place_bet(amount)
        self.pot += actual_bet
        if player.current_bet > self.current_bet:
            self.current_bet = player.current_bet

    def process_action(self, action: str, amount: int = 0) -> str:
        result = self._execute_move(action, amount)
        return result

    def _execute_move(self, action: str, amount: int = 0) -> str:
        current_p = self.players[self.active_player_index]
        
        # action text handling
        if action == "fold":
            current_p.last_action_text = "Fold"
        elif action == "check":
            current_p.last_action_text = "Check"
        elif action == "call":
            current_p.last_action_text = "Call"
        elif action == "raise":
            current_p.last_action_text = f"Raise ${amount}"
        elif action == "bet":
            current_p.last_action_text = f"Bet ${amount}"

        if action in current_p.actions:
            current_p.actions[action] += 1

        if action == 'fold':
            current_p.is_folded = True
            active = [p for p in self.players if not p.is_folded]
            if len(active) == 1:
                self._end_hand(winner=active[0])
                return "Hand Over"

        elif action == 'check':
            if current_p.current_bet < self.current_bet:
                return "Cannot check, must call."
        
        elif action == 'call':
            needed = self.current_bet - current_p.current_bet
            self._post_bet(current_p, needed)
            
        elif action == 'bet' or action == 'raise':
            limit = self.config.get('raise_limit', 0)
            if limit > 0 and amount > limit: return f"Limit is {limit}"
            if amount < self.current_bet + self.big_blind: return "Raise too small"
            diff = amount - current_p.current_bet
            self._post_bet(current_p, diff)
            current_p.actions['raise'] += 1

        self.actions_this_round += 1

        if self._is_betting_round_over():
            self._advance_stage()
        else:
            self._next_turn()
            
        return "OK"

    def _next_turn(self):
        """Finds next active player."""
        start = self.active_player_index
        n = len(self.players)
        for i in range(1, n + 1):
            idx = (start + i) % n
            p = self.players[idx]
            if not p.is_folded and not p.is_all_in:
                self.active_player_index = idx
                return

    def process_bot_turn(self):
        """Executes exactly ONE bot move."""
        if self.stage == SHOWDOWN or self.winner: return

        active_p = self.players[self.active_player_index]
        if active_p.is_bot:
            action, val = get_bot_move(self, active_p)
            self._execute_move(action, val)

    def _is_betting_round_over(self) -> bool:
        active = [p for p in self.players if not p.is_folded and not p.is_all_in]
        if not active: return True 

        target = self.current_bet
        for p in active:
            if p.current_bet != target: return False

        if self.actions_this_round < len(active):
             return False

        return True

    def _advance_stage(self):
        for p in self.players:
            if(p.last_action_text != "Fold"):
                p.last_action_text = ""

        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0
        self.actions_this_round = 0
        
        if self.stage == PREFLOP:
            self.stage = FLOP
            self.community_cards.extend(self.deck.deal(3))
        elif self.stage == FLOP:
            self.stage = TURN
            self.community_cards.extend(self.deck.deal(1))
        elif self.stage == TURN:
            self.stage = RIVER
            self.community_cards.extend(self.deck.deal(1))
        elif self.stage == RIVER:
            self.stage = SHOWDOWN
            self._resolve_showdown()
            return

        active_money = [p for p in self.players if not p.is_folded and not p.is_all_in]
        if len(active_money) < 2:
             self._advance_stage()
             return

        n = len(self.players)
        start = self.dealer_index
        for i in range(1, n + 1):
             idx = (start + i) % n
             p = self.players[idx]
             if not p.is_folded and not p.is_all_in:
                 self.active_player_index = idx
                 break


    def _resolve_showdown(self):
        active = [p for p in self.players if not p.is_folded]
        if not active: return
        
        scores = []
        for p in active:
            score = HandEvaluator.evaluate(p.hand + self.community_cards)
            scores.append((p, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # check for ties (split pot)
        winners = [scores[0][0]]
        for i in range(1, len(scores)):
            if scores[i][1] == scores[0][1]:
                winners.append(scores[i][0])
            else:
                break
        
        if len(winners) == 1:
            self._end_hand(winners[0])
        else:
            self._end_hand(None, winners=winners)

    def _end_hand(self, winner: Optional[Player], winners: List[Player] = None):
        if winner:
            winner.balance += self.pot
            self.winner = winner
            if not winner.is_bot:
                 self.db.update_balance(winner.id, self.pot)
                 self.db.record_hand_stats(winner.id, True, self.pot, 0, winner.actions)
        elif winners:
            split = self.pot // len(winners)
            for w in winners:
                w.balance += split
                if not w.is_bot:
                    self.db.update_balance(w.id, split)
            self.winner = None

        if winner:
            for p in self.players:
                if p != winner and not p.is_bot:
                    self.db.update_balance(p.id, -p.current_bet) # Simplified loss calc
                    
        self.stage = SHOWDOWN

    def leave_game(self, player_id: int):
        """Safely saves state when a player leaves."""
        p = next((p for p in self.players if p.id == player_id), None)
        if p:
            # forfeit bet if left early
            with self.db._get_connection() as conn:
                conn.execute("UPDATE players SET balance=? WHERE id=?", (p.balance, p.id))