# Connect Four game logic

class ConnectFour:
    ROWS = 6
    COLS = 7

    def __init__(self):
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.turn = 0  # 0: player1, 1: player2
        self.winner = None

    def reset(self):
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.turn = 0
        self.winner = None

    def make_move(self, col, player):
        if self.winner is not None:
            return False
        for row in reversed(range(self.ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = player
                if self.check_win(row, col, player):
                    self.winner = player
                self.turn = 1 - self.turn
                return True
        return False

    def check_win(self, row, col, player):
        def count(dx, dy):
            cnt = 0
            x, y = col, row
            while 0 <= x < self.COLS and 0 <= y < self.ROWS and self.board[y][x] == player:
                cnt += 1
                x += dx
                y += dy
            return cnt - 1
        directions = [ (1,0), (0,1), (1,1), (1,-1) ]
        for dx, dy in directions:
            total = 1 + count(dx, dy) + count(-dx, -dy)
            if total >= 4:
                return True
        return False
