import requests

SERVER_URL = 'http://localhost:5000'

class HTTPClient:
    def __init__(self, player_name):
        self.player = player_name
        self.room_id = None

    def create_room(self):
        resp = requests.post(f'{SERVER_URL}/create_room', json={'player': self.player}, timeout=3)
        data = resp.json()
        self.room_id = data.get('room_id')
        return data

    def join_room(self, room_id):
        resp = requests.post(f'{SERVER_URL}/join_room', json={'player': self.player, 'room_id': room_id}, timeout=3)
        if resp.status_code == 200:
            self.room_id = room_id
            return resp.json()
        else:
            raise Exception(resp.json().get('error', 'Gagal join room'))

    def quick_join(self):
        resp = requests.post(f'{SERVER_URL}/quick_join', json={'player': self.player}, timeout=3)
        data = resp.json()
        self.room_id = data.get('room_id')
        return data

    def lobby_status(self):
        resp = requests.get(f'{SERVER_URL}/lobby_status', params={'room_id': self.room_id}, timeout=3)
        return resp.json()

    def set_ready(self):
        resp = requests.post(f'{SERVER_URL}/set_ready', json={'player': self.player, 'room_id': self.room_id}, timeout=3)
        return resp.json()

    def game_state(self):
        resp = requests.get(f'{SERVER_URL}/game_state', params={'room_id': self.room_id}, timeout=3)
        return resp.json()

    def make_move(self, col):
        resp = requests.post(f'{SERVER_URL}/make_move', json={'player': self.player, 'room_id': self.room_id, 'col': col}, timeout=3)
        return resp.json()