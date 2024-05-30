import socket
import threading
import sqlite3
from datetime import datetime
import json

# Veritabanı işlemleri için sınıf
class Database:
    def __init__(self, db_name='chat.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                sender TEXT,
                                receiver TEXT,
                                message TEXT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS groups (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                group_name TEXT UNIQUE)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS group_members (
                                group_id INTEGER,
                                username TEXT,
                                FOREIGN KEY (group_id) REFERENCES groups(id),
                                FOREIGN KEY (username) REFERENCES users(username))''')
     
        self.connection.commit()

    def add_user(self, username):
        try:
            self.cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            pass
        
    def get_all_users(self, username):
        self.cursor.execute('SELECT username FROM users')
        data =  [row[0] for row in self.cursor.fetchall()]
        data.remove(username)
        print(f'data: {data}')
        return data

    def check_user(self, username):
        self.cursor.execute('SELECT username FROM users WHERE username=?', (username,))
        return self.cursor.fetchone()

    def add_message(self, sender, receiver, message):
        self.cursor.execute('INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)', 
                            (sender, receiver, message))
        self.connection.commit()

    def get_messages(self, user):
        self.cursor.execute('SELECT sender, message, timestamp FROM messages WHERE receiver=?', (user,))
        return self.cursor.fetchall()

    def search_messages(self, user, keyword):
        data = self.get_messages(user)
        keyword_data = ''
        for message in data:
            if keyword in message[1]:
                keyword_data += f'{message[1]} !!@@!!'
        return keyword_data

    def create_group(self, group_name, members):    
        self.cursor.execute('INSERT INTO groups (group_name) VALUES (?)', (group_name,))
        group_id = self.cursor.lastrowid
        for member in members:
            self.cursor.execute('INSERT INTO group_members (group_id, username) VALUES (?, ?)', (group_id, member))
        self.connection.commit()

    def get_groups(self, username):
        self.cursor.execute('SELECT group_name FROM groups WHERE id IN (SELECT group_id FROM group_members WHERE username=?)', (username,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_group_members(self, group_name):
        self.cursor.execute('SELECT username FROM group_members WHERE group_id=(SELECT id FROM groups WHERE group_name=?)', (group_name,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_all_groups(self):
        self.cursor.execute('SELECT group_name FROM groups')
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()

# Sunucu işlemleri için sınıf
class Server:
    def __init__(self, host='127.0.0.1', port=5667):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        self.clients = {}
        self.db = Database()
    
    def __format_all_messages(self, db_result, me):
        messages = ''
        for message in db_result:
            messages += f'{me}->{message[0]}: {message[1]} ({message[2]})'

        return messages

    def single_broadcast(self, message, _client):
        for client in self.clients:
            if client != _client:
                try:
                    message = f'{message['data']['sender']} -> {message['data']['message']}'.encode('utf-8')
                    client.send(message)
                except Exception as e:
                    print(f'Error while broadcasting message: {e}')
    
    def broadcast_to_group(self, message, group_members):
        for client, username in self.clients.items():
            if username in group_members:
                try:
                    msg = f'{message['data']['sender']}({message['data']['group_name']}) -> {message['data']['message']}'
                    client.send(msg.encode('utf-8'))
                except Exception as e:
                    print(f'Error while broadcasting message to group: {e}')

    def handle_client(self, client):
        while True:
            try:
                message = client.recv(2048).decode('utf-8')
                if message:
                    data = json.loads(message)
                    if data['command'] == 'send_message':
                        self.db.add_message(data['data']['sender'], data['data']['receiver'], data['data']['message'])
                        self.single_broadcast(data, client)
                    elif data['command'] == 'get_my_messages':
                        db_result = self.db.get_messages(data['data']['username'])
                        sending_data = self.__format_all_messages(db_result, data['data']['username'])                        
                        client.send(json.dumps(sending_data).encode('utf-8'))
                    elif data['command'] == 'list_users':
                        db_result = self.db.get_all_users(data['data']['username'])
                        client.send(json.dumps(db_result).encode('utf-8'))
                    elif data['command'] == 'search_message_by_key':
                        db_result = self.db.search_messages(data['data']['username'], data['data']['keyword'])
                        client.send(json.dumps(db_result).encode('utf-8'))
                    elif data['command'] == 'create_group':
                        # seperate member with comma
                        members = data['data']['group_members'].split(',')
                        members_formatted = []
                        for member in members:
                            members_formatted.append(member.strip())
                        self.db.create_group(data['data']['group_name'], members_formatted)
                        client.send('Group created successfully'.encode('utf-8'))
                    elif data['command'] == 'send_message_to_group':
                        group_members = self.db.get_group_members(data['data']['group_name'])
                        self.broadcast_to_group(data, group_members)
                    elif data['command'] == 'list_my_groups':
                        db_result = self.db.get_groups(data['data']['username'])
                        client.send(json.dumps(db_result).encode('utf-8'))
                    elif data['command'] == 'list_all_groups':
                        db_result = self.db.get_all_groups()
                        client.send(json.dumps(db_result).encode('utf-8'))
            except Exception as e:
                print(f'Error while handling client: {e}')
                break

    def remove(self, client):
        if client in self.clients:
            client.close()
            del self.clients[client]

    def run(self):
        print("Server is running...")
        while True:
            client, address = self.server.accept()
            username = client.recv(1024).decode('utf-8')
            self.db.add_user(username)
            self.clients[client] = username
            print(f'{username} connected from {address}')
            client.send('Connected to the server.'.encode('utf-8'))
            threading.Thread(target=self.handle_client, args=(client,)).start()


if __name__ == "__main__":
    server = Server()
    server.run()
