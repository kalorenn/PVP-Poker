"""
something
"""

import pygame
import math
from typing import Optional, List
from .game_engine import PokerGame, PREFLOP, FLOP, TURN, RIVER, SHOWDOWN
from .database import DatabaseManager

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BG_COLOR = (34, 139, 34)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GRAY = (100, 100, 100)
GOLD = (255, 215, 0)
BUTTON_COLOR = (50, 50, 200)
SLIDER_BG = (200, 200, 200)
SLIDER_FILL = (50, 200, 50)
INPUT_ACTIVE = (200, 200, 255)
INPUT_INACTIVE = (240, 240, 240)

class PokerUI:
    def __init__(self, db: DatabaseManager):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Texas Hold'em Simulator")
        self.clock = pygame.time.Clock()
        
        self.db = db
        self.game: Optional[PokerGame] = None
        
        # Config State
        self.config = {
            'mode': 'PVE',
            'bot_count': 1,
            'small_blind': 10,
            'raise_limit': 0
        }
        
        # Fonts
        self.font = pygame.font.SysFont('Arial', 24)
        self.large_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.card_font = pygame.font.SysFont('Arial', 32, bold=True)

        self.ui_state = "LOGIN"
        self.message = ""
        self.running = True
        
        # UI Elements
        self.p1_name = ""
        self.p2_name = ""
        self.active_input_idx = -1
        self.input_rects = [
            pygame.Rect(SCREEN_WIDTH//2 - 150, 300, 300, 50),
            pygame.Rect(SCREEN_WIDTH//2 - 150, 400, 300, 50)
        ]
        
        self.leaderboard_data = []
        
        self.show_raise_menu = False
        self.raise_amount = 0
        self.slider_rect = pygame.Rect(0, 0, 0, 0)
        self.dragging_slider = False
        self.buttons = []

        self.last_bot_move_time = 0

    def run(self):
        while self.running:
            self.handle_events()
            self._update_game_logic()
            self.draw()
            self.clock.tick(30)
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.ui_state == "LOGIN":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_login_clicks(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self._handle_login_typing(event)
            
            elif self.ui_state == "OPTIONS":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_options_clicks(event.pos)
            
            elif self.ui_state == "LEADERBOARD":
                 if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_leaderboard_clicks(event.pos)
            
            elif self.ui_state in ["GAME", "MENU", "INTERSTITIAL", "GAMEOVER"]:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_game_general_clicks(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging_slider = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_slider and self.show_raise_menu:
                        self._update_slider(event.pos[0])

    def _handle_game_general_clicks(self, pos):
        for rect, action, param in self.buttons:
            if rect.collidepoint(pos):
                if action == "leave_table":
                    if self.game:
                        self.game.leave_game(self.game.players[0].id)
                    self.game = None
                    self.ui_state = "LOGIN"
                    return
                elif action == "deal_hand": # Handle Play Again
                     self.game.start_new_hand()
                     self.ui_state = "GAME" if self.game.mode == "PVE" else "INTERSTITIAL"
                     return

        if self.ui_state == "MENU":
            # For menu, we usually check Start Hand button
            for rect, action, param in self.buttons:
                if rect.collidepoint(pos):
                    if action == "deal_hand":
                        self.game.start_new_hand()
                        if self.game.mode == "PVE":
                            self.ui_state = "GAME"
                        else:
                            self.ui_state = "INTERSTITIAL"

        elif self.ui_state == "INTERSTITIAL":
            self.ui_state = "GAME"
            #FIX IS HERE
            return
        
        elif self.ui_state == "GAMEOVER":
             # Click usually resets to menu or new hand
             self.game.start_new_hand()
             if self.game.mode == "PVE":
                 self.ui_state = "GAME"
             else:
                 self.ui_state = "INTERSTITIAL"

        elif self.ui_state == "GAME":
             self._handle_gameplay_clicks(pos)

    def _handle_login_clicks(self, pos):
        self.active_input_idx = -1
        for i, rect in enumerate(self.input_rects):
            if rect.collidepoint(pos):
                self.active_input_idx = i
        
        for rect, action, param in self.buttons:
            if rect.collidepoint(pos):
                if action == "start_pvp":
                    self._initialize_game(mode="PVP")
                elif action == "start_pve":
                    self._initialize_game(mode="PVE")
                elif action == "show_leaderboard":
                    self.leaderboard_data = self.db.get_leaderboard()
                    self.ui_state = "LEADERBOARD"
                elif action == "show_options":
                    self.ui_state = "OPTIONS"

    def _handle_options_clicks(self, pos):
        for rect, action, param in self.buttons:
            if rect.collidepoint(pos):
                if action == "back_login":
                    self.ui_state = "LOGIN"
                elif action == "toggle_setting":
                    key, delta = param
                    current = self.config[key]
                    
                    if key == 'bot_count':
                        self.config[key] = max(1, min(4, current + delta))
                    elif key == 'small_blind':
                        self.config[key] = max(5, current + delta)
                    elif key == 'raise_limit':
                        self.config[key] = max(0, current + delta)

    def _handle_leaderboard_clicks(self, pos):
        for rect, action, param in self.buttons:
            if rect.collidepoint(pos):
                if action == "back_login":
                    self.ui_state = "LOGIN"
                elif action == "delete_player":
                    self.db.delete_player(param)
                    self.leaderboard_data = self.db.get_leaderboard()

    def _handle_login_typing(self, event):
        if self.active_input_idx == 0:
            if event.key == pygame.K_BACKSPACE: self.p1_name = self.p1_name[:-1]
            else: 
                if len(self.p1_name) < 12: self.p1_name += event.unicode
        elif self.active_input_idx == 1:
            if event.key == pygame.K_BACKSPACE: self.p2_name = self.p2_name[:-1]
            else:
                if len(self.p2_name) < 12: self.p2_name += event.unicode

    def _update_game_logic(self):
        """Handles timed events like Bot moves."""
        if not self.game or self.ui_state != "GAME": return
        if self.game.stage == SHOWDOWN or self.game.winner: return

        # Check if active player is Bot
        active_p = self.game.players[self.game.active_player_index]
        if active_p.is_bot:
            current_time = pygame.time.get_ticks()
            # 1000 ms = 1 second delay
            if current_time - self.last_bot_move_time > 1000:
                self.game.process_bot_turn()
                self.last_bot_move_time = current_time

    def _initialize_game(self, mode="PVE"):
        n1 = self.p1_name.strip() or "Player 1"
        p1_id, _ = self.db.get_or_create_player(n1)
        
        self.config['mode'] = mode
        
        if mode == "PVP":
            n2 = self.p2_name.strip() or "Player 2"
            if n1 == n2:
                self.message = "Names must be different!"
                return
            p2_id, _ = self.db.get_or_create_player(n2)
            self.config['p2_id'] = p2_id
        
        self.game = PokerGame(self.db, p1_id, self.config)
        self.ui_state = "MENU"
        self.message = ""

    def _handle_gameplay_clicks(self, pos):
        if self.game.stage == SHOWDOWN:
            self.ui_state = "GAMEOVER"
            return
        if self.show_raise_menu and self.slider_rect.collidepoint(pos):
            self.dragging_slider = True
            self._update_slider(pos[0])
            return
        
        for rect, action, param in self.buttons:
            if rect.collidepoint(pos):
                if action == "open_raise_menu":
                    self.show_raise_menu = True
                    current_p = self.game.players[self.game.active_player_index]
                    min_r = self.game.current_bet + self.game.big_blind
                    self.raise_amount = max(min_r, current_p.current_bet + self.game.big_blind)
                    self.raise_amount = min(self.raise_amount, current_p.balance + current_p.current_bet)
                elif action == "cancel_raise":
                    self.show_raise_menu = False
                    self.dragging_slider = False
                elif action == "set_raise":
                    self._calculate_pot_raise(param)
                elif action == "raise":
                    result = self.game.process_action(action, param)
                    self._post_action(result)
                else:
                    # Fold/Check/Call
                    result = self.game.process_action(action, param)
                    self._post_action(result)

    def _post_action(self, result):
        if result == "OK":
            self.show_raise_menu = False
            if self.game.mode == "PVP":
                self.ui_state = "INTERSTITIAL"
        elif result == "Hand Over":
            self.ui_state = "GAMEOVER"
        else:
            self.message = result

    def _calculate_pot_raise(self, multiplier):
        p = self.game.players[self.game.active_player_index]
        call_cost = self.game.current_bet - p.current_bet
        theoretical_pot = self.game.pot + call_cost
        raise_add = int(theoretical_pot * multiplier)
        total_bet = p.current_bet + call_cost + raise_add
        min_r = self.game.current_bet + self.game.big_blind
        max_r = p.balance + p.current_bet
        self.raise_amount = max(min_r, min(total_bet, max_r))

    def _update_slider(self, mouse_x):
        p = self.game.players[self.game.active_player_index]
        min_val = self.game.current_bet + self.game.big_blind
        max_val = p.balance + p.current_bet
        if max_val <= min_val: return
        slider_x = SCREEN_WIDTH // 2 - 200
        slider_w = 400
        ratio = (mouse_x - slider_x) / slider_w
        ratio = max(0.0, min(1.0, ratio))
        self.raise_amount = int(min_val + (max_val - min_val) * ratio)

    # --- DRAWING ---
    def draw(self):
        self.screen.fill(BG_COLOR)
        
        if self.ui_state == "LOGIN":
            self._draw_login_screen()
        elif self.ui_state == "OPTIONS":
            self._draw_options_screen()
        elif self.ui_state == "LEADERBOARD":
            self._draw_leaderboard_screen()
        elif self.ui_state == "MENU":
            self._draw_centered_text("Match Ready!", -50, size=60)
            self._create_button("Deal Hand", SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 50, "deal_hand", width=200, height=60)
            
        elif self.ui_state == "INTERSTITIAL":
            active_player = self.game.players[self.game.active_player_index]
            self.screen.fill(BLACK)
            self._draw_centered_text(f"{active_player.name}'s Turn", -20, color=WHITE)
            self._draw_centered_text("Click to Reveal Cards", 40, color=GRAY)
            
        elif self.ui_state == "GAME":
            self._draw_table()
            if self.show_raise_menu:
                self._draw_raise_menu()
            else:
                self._draw_main_buttons()
            if self.message:
                self._draw_centered_text(self.message, -200, color=RED)
                
        elif self.ui_state == "GAMEOVER":
            self._draw_table(show_all=True)
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            s.set_alpha(150)
            s.fill(BLACK)
            self.screen.blit(s, (0,0))
            
            winner = f"Winner: {self.game.winner.name}" if self.game.winner else "Split Pot"
            self._draw_centered_text(winner, -50, color=WHITE, size=60)
            self._draw_centered_text(f"Pot: ${self.game.pot}", 20, color=WHITE)
            
            # --- BUTTONS ---
            self.buttons = [] # Clear buttons for this frame
            
            # "Play Again" Button (Center)
            self._create_button("Play Again", SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 100, "deal_hand", width=200, height=60)
            
            # "Leave Table" Button (Bottom Right)
            menu_x = SCREEN_WIDTH - 180
            menu_y = SCREEN_HEIGHT - 140 # Positioned near bottom right
            self._create_button("Leave Table", menu_x, menu_y, "leave_table", width=150, height=60, color=(150, 50, 50))
        
        pygame.display.flip()

    def _draw_login_screen(self):
        self._draw_centered_text("Poker Simulator", -200, size=60)
        self.buttons = []
        
        # Labels
        lbl1 = self.font.render("Player 1 Name:", True, WHITE)
        self.screen.blit(lbl1, (self.input_rects[0].x, self.input_rects[0].y - 30))
        lbl2 = self.font.render("Player 2 Name (PVP):", True, WHITE)
        self.screen.blit(lbl2, (self.input_rects[1].x, self.input_rects[1].y - 30))

        # Input Boxes
        for i, rect in enumerate(self.input_rects):
            color = INPUT_ACTIVE if i == self.active_input_idx else INPUT_INACTIVE
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            text = self.p1_name if i == 0 else self.p2_name
            txt_surf = self.font.render(text, True, BLACK)
            self.screen.blit(txt_surf, (rect.x + 10, rect.y + 10))
        
        self._create_button("Play vs Bot", SCREEN_WIDTH//2 - 210, 500, "start_pve", width=200, height=60)
        self._create_button("1 vs 1 (Local)", SCREEN_WIDTH//2 + 10, 500, "start_pvp", width=200, height=60)
        
        self._create_button("Options", SCREEN_WIDTH//2 - 210, 580, "show_options", width=200, height=50, color=(100, 100, 100))
        self._create_button("Leaderboard", SCREEN_WIDTH//2 + 10, 580, "show_leaderboard", width=200, height=50, color=(100, 100, 100))
        
        if self.message:
             self._draw_centered_text(self.message, 250, color=RED)

    def _draw_options_screen(self):
        self._draw_centered_text("Game Options", -300, size=50)
        self.buttons = []
        
        def draw_setting_row(y, label, key, step):
            self.screen.blit(self.font.render(label, True, WHITE), (300, y))
            val_str = str(self.config[key])
            if key == 'raise_limit' and self.config[key] == 0: val_str = "No Limit"
            
            self._create_button("-", 600, y, "toggle_setting", (key, -step), width=40, height=30)
            self.screen.blit(self.font.render(val_str, True, GOLD), (660, y))
            self._create_button("+", 720, y, "toggle_setting", (key, step), width=40, height=30)

        draw_setting_row(200, "Number of Bots (1-4):", 'bot_count', 1)
        draw_setting_row(300, "Small Blind:", 'small_blind', 5)
        draw_setting_row(400, "Raise Limit:", 'raise_limit', 50)
        
        self._create_button("Back", 50, 50, "back_login", width=100)

    def _draw_leaderboard_screen(self):
        self._draw_centered_text("Top 10 Players", -300, size=50)
        self.buttons = []
        header_y = 150
        pygame.draw.line(self.screen, WHITE, (200, header_y + 30), (824, header_y + 30), 2)
        self.screen.blit(self.font.render("Rank", True, GOLD), (210, header_y))
        self.screen.blit(self.font.render("Name", True, GOLD), (300, header_y))
        self.screen.blit(self.font.render("Balance", True, GOLD), (500, header_y))
        self.screen.blit(self.font.render("Wins", True, GOLD), (650, header_y))
        
        start_y = 200
        for i, row in enumerate(self.leaderboard_data):
            y = start_y + i * 40
            name, bal, wins, pid = row
            self.screen.blit(self.font.render(f"#{i+1}", True, WHITE), (210, y))
            self.screen.blit(self.font.render(name[:12], True, WHITE), (300, y))
            self.screen.blit(self.font.render(f"${bal}", True, WHITE), (500, y))
            self.screen.blit(self.font.render(f"{wins}", True, WHITE), (650, y))
            self._create_button("X", 750, y, "delete_player", pid, width=30, height=30, color=(150, 0, 0))

        self._create_button("Back", 50, 50, "back_login", width=100)

    def _draw_table(self, show_all=False):
        # 1. Community Cards & Pot (Keep existing code)
        start_x = SCREEN_WIDTH // 2 - (5 * 80) // 2
        card_y = SCREEN_HEIGHT // 2 - 40
        for i, card in enumerate(self.game.community_cards):
            self._draw_card(card, start_x + i * 85, card_y)
        
        pot_text = self.large_font.render(f"Pot: ${self.game.pot}", True, WHITE)
        self.screen.blit(pot_text, (SCREEN_WIDTH // 2 - 50, card_y - 40))

        # 2. DYNAMIC SEATING LOGIC
        # In Hotseat (PVP), the Active Player should always be the "Hero" (Bottom)
        # In PVE (Bots), Player 0 is always "Hero".
        
        hero_index = 0 # Default for PVE
        if self.game.mode == "PVP" and not show_all:
             # If we are playing, the person acting is the Hero
             hero_index = self.game.active_player_index
        
        # Define Hero
        hero = self.game.players[hero_index]
        
        # Define Opponents (Everyone else)
        # We start checking from hero_index + 1 to wrap around
        opponents = []
        n = len(self.game.players)
        for i in range(1, n):
            idx = (hero_index + i) % n
            opponents.append(self.game.players[idx])

        # 3. Draw Opponents (Top Row)
        if opponents:
            area_width = SCREEN_WIDTH - 200
            spacing = area_width // len(opponents)
            start_opp_x = 100
            for i, bot in enumerate(opponents):
                x = start_opp_x + i * spacing
                y = 60 
                self._draw_player_area(bot, x, y, is_hero=False, reveal=show_all)

        # 4. Draw Hero (Bottom Left)
        self._draw_player_area(hero, 50, SCREEN_HEIGHT - 220, is_hero=True, reveal=True)

    def _draw_player_area(self, player, x, y, is_hero, reveal=False):
        is_active = (player == self.game.players[self.game.active_player_index])
        
        # Dimensions
        w, h = (300, 200) if is_hero else (180, 130)
        card_scale = 1.0 if is_hero else 0.8
        
        # Background Panel
        bg_rect = pygame.Rect(x, y, w, h)
        bg_col = (40, 40, 50) 
        border_col = GOLD if is_active else (100, 100, 100)
        
        pygame.draw.rect(self.screen, bg_col, bg_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_col, bg_rect, 3, border_radius=12)
        
        # Dealer Button
        if player == self.game.players[self.game.dealer_index]:
            btn_x = x + w - 20
            btn_y = y + 20
            pygame.draw.circle(self.screen, WHITE, (btn_x, btn_y), 15)
            pygame.draw.circle(self.screen, BLACK, (btn_x, btn_y), 15, 2)
            d_text = self.font.render("D", True, BLACK)
            d_rect = d_text.get_rect(center=(btn_x, btn_y))
            self.screen.blit(d_text, d_rect)

        # Text Info
        name_font = self.large_font if is_hero else self.font
        color = WHITE if is_active else GRAY
        
        # Name
        self.screen.blit(name_font.render(player.name[:12], True, color), (x + 15, y + 10))
        
        # Balance & Bet
        bal_str = f"${player.balance}"
        bet_str = "All-In" if player.is_all_in else f"Bet: ${player.current_bet}"
        
        # Action Text
        action_color = (100, 255, 100)
        action_text = self.font.render(player.last_action_text, True, action_color)

        if is_hero:
            self.screen.blit(self.font.render(bal_str, True, GOLD), (x + 15, y + 50))
            self.screen.blit(self.font.render(bet_str, True, WHITE), (x + 150, y + 50))
            self.screen.blit(action_text, (x + 15, y - 30)) 
            card_start_y = y + 90
        else:
            self.screen.blit(self.font.render(bal_str, True, GOLD), (x + 15, y + 35))
            self.screen.blit(self.font.render(bet_str, True, WHITE), (x + 15, y + 100))
            self.screen.blit(action_text, (x + 15, y + 125)) 
            card_start_y = y + 60

        # Draw Cards (ONLY if revealed)
        card_w = int(80 * card_scale)
        card_h = int(120 * card_scale)
        card_spacing = int(85 * card_scale)
        card_x_offset = 15 if is_hero else 80
        
        for k, card in enumerate(player.hand):
            cx = x + card_x_offset + k * card_spacing
            cy = card_start_y
            
            # MODIFIED: Removed the 'else' block for card backs.
            # We only draw if we are allowed to see the face (Hero or Showdown).
            if reveal or self.game.stage == SHOWDOWN:
                self._draw_card(card, cx, cy, w=card_w, h=card_h)

    def _draw_card(self, card, x, y, w=80, h=120):
        # Adjusted to accept dynamic width/height for scaling
        pygame.draw.rect(self.screen, WHITE, (x, y, w, h), border_radius=5)
        pygame.draw.rect(self.screen, BLACK, (x, y, w, h), 2)
        color = RED if card.suit in ['H', 'D'] else BLACK
        suit_sym = {'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'}.get(card.suit, card.suit)
        
        # Scale fonts slightly if small card
        font_s = self.card_font if w > 60 else self.font
        
        self.screen.blit(font_s.render(f"{card.rank}", True, color), (x + 5, y + 5))
        if w > 50:
             self.screen.blit(self.large_font.render(suit_sym, True, color), (x + 15, y + 35))
        else:
             self.screen.blit(self.font.render(suit_sym, True, color), (x + 15, y + 25))

    def _draw_card_back(self, x, y, w=80, h=120):
        pygame.draw.rect(self.screen, (0, 0, 150), (x, y, w, h), border_radius=5)
        pygame.draw.rect(self.screen, WHITE, (x, y, w, h), 2)

    def _draw_main_buttons(self):
        self.buttons = [] # It is safe to clear here if this is the only place drawing buttons for this state
        
        menu_x = SCREEN_WIDTH - 180
        menu_y = SCREEN_HEIGHT - 350
        btn_w = 150
        btn_h = 60
        spacing = 70
        
        p = self.game.players[self.game.active_player_index]
        
        # If it's a Bot's turn, we usually hide buttons, 
        # BUT we should still show "Leave Table" so you aren't stuck waiting!
        if p.is_bot:
             self._draw_centered_text("Bot Thinking...", 300, GOLD)
             # Draw Leave Button at the bottom position even if bot is thinking
             self._create_button("Leave Table", menu_x, menu_y + spacing * 3, "leave_table", width=btn_w, height=btn_h, color=(150, 50, 50))
             return

        call_cost = self.game.current_bet - p.current_bet
        
        # 1. Fold
        self._create_button("Fold", menu_x, menu_y, "fold", width=btn_w, height=btn_h, color=(150, 50, 50))
        
        # 2. Check/Call
        if call_cost == 0:
            self._create_button("Check", menu_x, menu_y + spacing, "check", width=btn_w, height=btn_h)
        else:
            self._create_button(f"Call ${call_cost}", menu_x, menu_y + spacing, "call", width=btn_w, height=btn_h)
            
        # 3. Raise
        self._create_button("Raise...", menu_x, menu_y + spacing * 2, "open_raise_menu", width=btn_w, height=btn_h)
        
        # 4. Leave Table (New Position)
        self._create_button("Leave Table", menu_x, menu_y + spacing * 3, "leave_table", width=btn_w, height=btn_h, color=(100, 50, 50))

    def _draw_raise_menu(self):
        self.buttons = []
        panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 250, SCREEN_HEIGHT - 220, 500, 200)
        pygame.draw.rect(self.screen, (50, 50, 50), panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, panel_rect, 2)
        slider_x = SCREEN_WIDTH // 2 - 200
        slider_y = SCREEN_HEIGHT - 160
        slider_w = 400
        self.slider_rect = pygame.Rect(slider_x, slider_y, slider_w, 10)
        pygame.draw.rect(self.screen, SLIDER_BG, self.slider_rect, border_radius=5)
        p = self.game.players[self.game.active_player_index]
        min_val = self.game.current_bet + self.game.big_blind
        max_val = p.balance + p.current_bet
        ratio = 1.0
        if max_val > min_val:
            ratio = (self.raise_amount - min_val) / (max_val - min_val)
        handle_x = slider_x + (slider_w * ratio)
        pygame.draw.circle(self.screen, SLIDER_FILL, (int(handle_x), slider_y + 5), 15)
        text = self.font.render(f"Raise To: ${self.raise_amount}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - 50, slider_y - 40))
        btn_y = slider_y + 30
        self._create_button("1/2 Pot", slider_x, btn_y, "set_raise", 0.5, width=120, height=40)
        self._create_button("Pot", slider_x + 140, btn_y, "set_raise", 1.0, width=120, height=40)
        confirm_y = btn_y + 60
        self._create_button("Confirm", slider_x, confirm_y, "raise", self.raise_amount, width=190, color=(0, 150, 0))
        self._create_button("Cancel", slider_x + 210, confirm_y, "cancel_raise", width=190, color=(150, 0, 0))

    def _draw_centered_text(self, text, y_offset, color=WHITE, size=None):
        font = self.large_font if size else self.font
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset))
        self.screen.blit(surf, rect)

    def _create_button(self, text, x, y, action, param=0, width=120, height=50, color=None):
        mouse_pos = pygame.mouse.get_pos()
        rect = pygame.Rect(x, y, width, height)
        base_color = color if color else BUTTON_COLOR
        hover_color = tuple(min(c + 30, 255) for c in base_color)
        draw_color = hover_color if rect.collidepoint(mouse_pos) else base_color
        pygame.draw.rect(self.screen, draw_color, rect, border_radius=8)
        text_surf = self.font.render(text, True, WHITE)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)
        self.buttons.append((rect, action, param))