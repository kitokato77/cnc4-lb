import pygame
import sys
from http_client import HTTPClient
from connect_four import ConnectFour
import requests

pygame.init()
WIDTH, HEIGHT = 700, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Multiplayer Connect Four')
FONT = pygame.font.SysFont('Arial', 32)
SMALL_FONT = pygame.font.SysFont('Arial', 24)

COLORS = [(200,200,200), (255,0,0), (255,255,0)]

# State
STATE_MENU = 'menu'
STATE_LOBBY = 'lobby'
STATE_GAME = 'game'
STATE_WIN = 'win'
STATE_LOSE = 'lose'

class GameClient:
    def __init__(self):
        self.state = STATE_MENU
        self.http = None
        self.player_name = ''
        self.room_id = ''
        self.lobby_ready = False
        self.lobby_players = []
        self.lobby_ready_status = {}
        self.connect4 = ConnectFour()
        self.my_idx = 0
        self.winner = None
        self.menu_notification = "" 

    def draw_menu(self):
        SCREEN.fill((30,30,60))
        title = FONT.render('Connect Four Multiplayer', True, (255,255,255))
        SCREEN.blit(title, (WIDTH//2-title.get_width()//2, 60))
        name_label = SMALL_FONT.render('Nama:', True, (255,255,255))
        SCREEN.blit(name_label, (WIDTH//2-100, 150))
        name_box = pygame.Rect(WIDTH//2-20, 145, 200, 40)
        pygame.draw.rect(SCREEN, (255,255,255), name_box, 2)
        name_text = SMALL_FONT.render(self.player_name, True, (255,255,255))
        SCREEN.blit(name_text, (WIDTH//2-10, 150))
        btn_create = pygame.Rect(WIDTH//2-120, 220, 240, 50)
        btn_join = pygame.Rect(WIDTH//2-120, 290, 240, 50)
        btn_join_code = pygame.Rect(WIDTH//2-120, 360, 240, 50)
        pygame.draw.rect(SCREEN, (0,120,255), btn_create)
        pygame.draw.rect(SCREEN, (0,200,100), btn_join)
        pygame.draw.rect(SCREEN, (200,120,0), btn_join_code)
        SCREEN.blit(FONT.render('Buat Room', True, (255,255,255)), (WIDTH//2-70, 230))
        SCREEN.blit(FONT.render('Join Cepat', True, (255,255,255)), (WIDTH//2-70, 300))
        # Input box for room code
        code_label = SMALL_FONT.render('Kode:', True, (255,255,255))
        SCREEN.blit(code_label, (WIDTH//2-100, 430))
        SCREEN.blit(FONT.render('Join Kode', True, (255,255,255)), (WIDTH//2-70, 370))
        code_box = pygame.Rect(WIDTH//2-20, 425, 200, 40)
        pygame.draw.rect(SCREEN, (255,255,255), code_box, 2)
        code_text = SMALL_FONT.render(self.room_id, True, (255,255,255))
        SCREEN.blit(code_text, (WIDTH//2-10, 430))
        # Tampilkan notifikasi jika ada
        if self.menu_notification:
            notif = SMALL_FONT.render(self.menu_notification, True, (255, 80, 80))
            SCREEN.blit(notif, (WIDTH//2 - notif.get_width()//2, 490))
        return name_box, btn_create, btn_join, btn_join_code, code_box


    def draw_lobby(self):
        SCREEN.fill((30,60,30))
        title = FONT.render(f'Lobby Room: {self.room_id}', True, (255,255,255))
        SCREEN.blit(title, (WIDTH//2-title.get_width()//2, 60))
        y = 150
        for p in self.lobby_players:
            ready = self.lobby_ready_status.get(p, False)
            txt = SMALL_FONT.render(f'{p} - {"Ready" if ready else "Belum"}', True, (0,255,0) if ready else (255,255,0))
            SCREEN.blit(txt, (WIDTH//2-100, y))
            y += 40
        btn_ready = pygame.Rect(WIDTH//2-80, 350, 160, 50)
        pygame.draw.rect(SCREEN, (0,200,100), btn_ready)
        SCREEN.blit(FONT.render('Ready', True, (255,255,255)), (WIDTH//2-40, 360))
        return btn_ready

    def draw_board(self, board, grid_top=100):
        grid_left = 50
        cell_size = 80
        # Draw grid background
        pygame.draw.rect(SCREEN, (0, 60, 200), (grid_left, grid_top, 7*cell_size, 6*cell_size), border_radius=12)
        # Draw circles for each cell
        for r in range(6):
            for c in range(7):
                color = COLORS[board[r][c]]
                center = (grid_left + c*cell_size + cell_size//2, grid_top + r*cell_size + cell_size//2)
                pygame.draw.circle(SCREEN, color, center, cell_size//2 - 6)
        # Draw grid lines
        for c in range(8):
            pygame.draw.line(SCREEN, (255,255,255), (grid_left + c*cell_size, grid_top), (grid_left + c*cell_size, grid_top + 6*cell_size), 2)
        for r in range(7):
            pygame.draw.line(SCREEN, (255,255,255), (grid_left, grid_top + r*cell_size), (grid_left + 7*cell_size, grid_top + r*cell_size), 2)
            
    def draw_game(self, board, turn, my_turn, player_names=None):
        # Draw top bar for turn info
        SCREEN.fill((20, 20, 60))
        bar_height = 60
        pygame.draw.rect(SCREEN, (30, 30, 90), (0, 0, WIDTH, bar_height))
        # Show turn info
        if player_names and len(player_names) == 2:
            turn_text = f'Giliran: {player_names[turn]}'
        else:
            turn_text = f'Giliran: {"Anda" if my_turn else "Lawan"}'
        info = FONT.render(turn_text, True, (255,255,0) if my_turn else (255,255,255))
        SCREEN.blit(info, (WIDTH//2 - info.get_width()//2, bar_height//2 - info.get_height()//2 + 2))
        # Draw the board below the top bar
        grid_top = bar_height + 10
        self.draw_board(board, grid_top=grid_top)
        # Draw player names below the grid
        if player_names and len(player_names) == 2:
            cell_size = 80
            grid_left = 50
            grid_height = 6 * cell_size
            y_pos = grid_top + grid_height + 15
            p1 = SMALL_FONT.render(f'P1: {player_names[0]}', True, (255,0,0))
            p2 = SMALL_FONT.render(f'P2: {player_names[1]}', True, (255,255,0))
            SCREEN.blit(p1, (grid_left, y_pos))
            SCREEN.blit(p2, (WIDTH - grid_left - p2.get_width(), y_pos))

    def draw_win(self, menang):
        SCREEN.fill((0,0,0))
        msg = 'MENANG!' if menang else 'KALAH!'
        txt = FONT.render(msg, True, (255,255,0) if menang else (255,0,0))
        SCREEN.blit(txt, (WIDTH//2-txt.get_width()//2, HEIGHT//2-txt.get_height()//2 - 40))
        # Draw "Return to Menu" button
        btn_menu = pygame.Rect(WIDTH//2-100, HEIGHT//2+40, 200, 50)
        pygame.draw.rect(SCREEN, (0,120,255), btn_menu)
        btn_text = FONT.render('Menu', True, (255,255,255))
        SCREEN.blit(btn_text, (WIDTH//2-btn_text.get_width()//2, HEIGHT//2+50))
        return btn_menu

    def run(self):
        clock = pygame.time.Clock()
        input_active = False
        code_input_active = False
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.state == STATE_MENU:
                    name_box, btn_create, btn_join, btn_join_code, code_box = self.draw_menu()
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if name_box.collidepoint(event.pos):
                            input_active = True
                            code_input_active = False
                        elif code_box.collidepoint(event.pos):
                            code_input_active = True
                            input_active = False
                        else:
                            input_active = False
                            code_input_active = False
                        if btn_create.collidepoint(event.pos) and self.player_name:
                            self.menu_notification = ""
                            self.http = HTTPClient(self.player_name)
                            data = self.http.create_room()
                            self.room_id = data['room_id']
                            self.state = STATE_LOBBY
                        if btn_join.collidepoint(event.pos) and self.player_name:
                            self.menu_notification = ""
                            self.http = HTTPClient(self.player_name)
                            data = self.http.quick_join()
                            self.room_id = data['room_id']
                            self.state = STATE_LOBBY
                        if btn_join_code.collidepoint(event.pos) and self.player_name and self.room_id:
                            self.menu_notification = ""
                            self.http = HTTPClient(self.player_name)
                            try:
                                data = self.http.join_room(self.room_id)
                                self.room_id = data['room_id']
                                self.state = STATE_LOBBY
                            except requests.exceptions.Timeout:
                                self.menu_notification = "Server timeout. Coba lagi."
                            except Exception as e:
                                self.menu_notification = "Room tidak ditemukan atau sudah penuh."
                    if event.type == pygame.KEYDOWN:
                        if input_active:
                            if event.key == pygame.K_BACKSPACE:
                                self.player_name = self.player_name[:-1]
                            elif len(self.player_name) < 16 and event.unicode.isprintable():
                                self.player_name += event.unicode
                        elif code_input_active:
                            if event.key == pygame.K_BACKSPACE:
                                self.room_id = self.room_id[:-1]
                            elif len(self.room_id) < 16 and event.unicode.isprintable():
                                self.room_id += event.unicode
                elif self.state == STATE_LOBBY:
                    btn_ready = self.draw_lobby()
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if btn_ready.collidepoint(event.pos):
                            if self.http is not None:
                                self.http.set_ready()
                    # Poll lobby status
                    if self.http is not None:
                        lobby = self.http.lobby_status()
                        self.lobby_players = lobby.get('players', [])
                        self.lobby_ready_status = lobby.get('ready', {})
                        if len(self.lobby_players) == 2 and all(self.lobby_ready_status.values()):
                            # Tentukan index player
                            self.my_idx = self.lobby_players.index(self.player_name)
                            self.state = STATE_GAME
                            self.connect4.reset()
                elif self.state == STATE_GAME:
                    if self.http is not None:
                        state = self.http.game_state()
                        board = state.get('board', [[0]*7 for _ in range(6)])
                        turn = state.get('turn', 0)
                        winner = state.get('winner', None)
                        my_turn = (turn == self.my_idx)
                        player_names = self.lobby_players if hasattr(self, 'lobby_players') else None
                        self.draw_game(board, turn, my_turn, player_names)
                        if winner:
                            if winner == self.player_name:
                                self.state = STATE_WIN
                            else:
                                self.state = STATE_LOSE
                        if event.type == pygame.MOUSEBUTTONDOWN and my_turn:
                            x, y = event.pos
                            # Only allow click inside the grid area
                            grid_left = 50
                            grid_top = 10
                            cell_size = 80
                            if grid_left <= x < grid_left + 7*cell_size and grid_top <= y < grid_top + 6*cell_size:
                                col = (x - grid_left) // cell_size
                                if 0 <= col < 7:
                                    self.http.make_move(col)
                elif self.state == STATE_WIN:
                    btn_menu = self.draw_win(True)
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if btn_menu.collidepoint(event.pos):
                            self.state = STATE_MENU
                            self.player_name = ''
                            self.room_id = ''
                            self.menu_notification = ''
                            self.lobby_players = []
                            self.lobby_ready_status = {}
                            self.http = None
                elif self.state == STATE_LOSE:
                    btn_menu = self.draw_win(False)
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if btn_menu.collidepoint(event.pos):
                            self.state = STATE_MENU
                            self.player_name = ''
                            self.room_id = ''
                            self.menu_notification = ''
                            self.lobby_players = []
                            self.lobby_ready_status = {}
                            self.http = None
            pygame.display.flip()
            clock.tick(30)

def main():
    GameClient().run()

if __name__ == '__main__':
    main()
