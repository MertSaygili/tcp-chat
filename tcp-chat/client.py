import socket
import threading
import time
import json

def receive_messages(client):
    while True:
        try:
            message = client.recv(1024).decode('utf-8')
            if message:
                if ')' in message and '->' in message:
                    splitted_message = message.split(')')
                    for msg in splitted_message:
                        msg.replace('(', '')
                        print(msg)
                if '!!@@!!' in message:
                    splitted_message = message.split('!!@@!!')
                    for msg in splitted_message:
                        print(msg)
                else:
                    print(message)
            else:
                break
        except:
            break

def main():
    username = input("Enter your username: ")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 5667))
    client.send(username.encode('utf-8'))

    threading.Thread(target=receive_messages, args=(client,)).start()

    while True:
        time.sleep(0.5)
        print('--------------------------------')
        print('0. Quit')
        print('1. Send a message')
        print('2. Get my messages')
        print('3. List all users')
        print('4. Search my message')
        print('5. Create a group')
        print('6. Send a message to group')
        print('7. List my groups')
        print('8. List all groups')
        print('--------------------------------')
        message = input()
        if message == '0':
            client.close()
            break
        elif message == '1':
            keep_talking = True
            print('Choose user to send message: ')
            receiver = input()
            print('For quit, type "quit"')
            print('Enter your message: ')
            while keep_talking:
                message = input()
                if message.lower() == 'quit':
                    keep_talking = False
                    break
                sending_message = {'command': 'send_message', 'data': {'sender': username, 'receiver': receiver, 'message': message}}
                json.dumps(sending_message).encode('utf-8')
                client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '2':
            sending_message = {'command': "get_my_messages", 'data': {'username': username}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '3':
            sending_message = {'command': 'list_users', 'data':{'username':username}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '4':
            print('Enter keyword: ')
            keyword = input()
            sending_message = {'command': 'search_message_by_key', 'data':{'username':username, 'keyword':keyword}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '5':
            print('Enter group name: ')
            group_name = input()
            print('Enter group members (separated by comma): ')
            group_members = input()
            sending_message = {'command': 'create_group', 'data': {'group_name': group_name, 'group_members': group_members}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '6':
            print('Enter group name: ')
            group_name = input()
            print('Enter your message: ')
            message = input()
            sending_message = {'command': 'send_message_to_group', 'data': {'sender': username, 'group_name': group_name, 'message': message}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '7':
            sending_message = {'command': 'list_my_groups', 'data': {'username': username}}
            client.send(json.dumps(sending_message).encode('utf-8'))
        elif message == '8':
            sending_message = {'command': 'list_all_groups', 'data': {'username': username}}
            client.send(json.dumps(sending_message).encode('utf-8'))

if __name__ == "__main__":
    main()
