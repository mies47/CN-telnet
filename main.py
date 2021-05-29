import os
import socket
import sys
import ipaddress
import json
import signal
import subprocess
import rsa
import pickle
import threading
import psycopg2 as pg
import pandas as pd
from datetime import datetime
from getpass import getpass

ENCODING = 'utf-8'
CHUNK_SIZE = 4096
PORTS_FILE = open('ports.json', 'r')
PORTS_DIC = json.load(PORTS_FILE)
PORTS_FILE.close()
MAX_RETRY = 10
LOG_MODE = False

def main():
    'Main method'

    if len(sys.argv) < 2:
        print('need more args!!')
        sys.exit(-1)

    if sys.argv[1] == 'client':
        print('Entering client mode...')
        client_mode()

    elif sys.argv[1] == 'server':
        print('Entering server mode...')
        encrypt = len(sys.argv) > 3 and sys.argv[3] == '-e'
        server_mode(int(sys.argv[2]), encrypt)



def sigint_handler(sig, frame):
    'Capture SIGINT signal and restart program'

    raise Exception('\nProcess stopped!\n')
    

def client_mode():
    '''Enter client mode
       handle client operations
       1- Send messages to host and port
       2- Send and recieve files
       3- Execute commands on server
       4- Scan open ports'''


    print('Want to connect to database to save commands for history...')
    connection = connect_to_database()

    while True:
        try:
            operation = input('telnet>').split(' ')
        except Exception as exc:
            print(exc)
            break

        add_history(connection, ' '.join(operation))
        if operation[0] == 'open':
            host, port = operation[1], operation[2]
            connected_socket = establish_connection(host, int(port), 5)
            public_key, private_key = None, None
            if not connected_socket:
                continue
            else:
                if len(operation) > 3 and operation[3] == '-e': # Check if encryption is desired
                    public_key = recv_public_key(connected_socket)
                    print(public_key)
                    client_public_key , private_key = rsa.newkeys(512)
                    send_public_key(connected_socket, client_public_key)
                while True:
                    try:
                        command = input(f'{host}:{port}>').split(' ')
                    except Exception as exc:
                        print(exc)
                        break

                    add_history(connection, ' '.join(command))

                    if command[0] == 'quit':
                        send_message(connected_socket, 'quit')
                        print('Waiting for server...')
                        recv_message(connected_socket)
                        break


                    if command[0] == 'send' and command[1] == 'message': 
                        #Case 1 send message
                        command_to_send = ' '.join(command)
                        send_message(connected_socket, command_to_send + (CHUNK_SIZE - len(command_to_send))* ' ')
                        send_message_to_host(connected_socket, public_key, private_key)
                    
                    elif command[0] == 'exec':
                        #Case 3 send  command for execution
                        success = send_message(connected_socket, ' '.join(command))
                        print('Sent command to server.') if success else print('Transmision failed.')
                        print('Waiting for server...')
                        print(recv_message(connected_socket))


                    elif command[0] == 'upload':
                        #Case 2 upload file
                        fileName = os.path.basename(command[1])
                        send_message(connected_socket, 'upload' + fileName + (CHUNK_SIZE - len(fileName) - 6)* ' ')
                        success = send_file(connected_socket, command[1])
                        print('Transmision was successful.') if success else print('Transmision failed.')
                        print(recv_message(connected_socket))

                    elif command[0] == 'download':
                        #Case 2 download file
                        fileName = os.path.basename(command[1])
                        send_message(connected_socket, 'download' + command[1] + (CHUNK_SIZE - len(command[1]) - 8)* ' ')
                        success = recv_file(connected_socket, fileName)
                        print('Transmision was successful.') if success else print('Transmision failed.')
                
                connected_socket.close()

        elif operation[0] == 'scan':
            #Case 4 scan ports
            scan_ports(operation[1], operation[2])
        
        elif operation[0] == 'history':
            #Case 5 get all histories
            get_history(connection)
        
        elif operation[0] == 'log':
            #Case 6 print undecrypted values
            global LOG_MODE
            LOG_MODE = not LOG_MODE
            print(f'Logging has changed to {LOG_MODE}')


def server_mode(port:int, encrypt:bool=False):
    '''Enter server mode
       Listen on the given port'''

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('127.0.0.1', port))
        server_socket.listen()
        keys = {}

        if encrypt:
            public, private = rsa.newkeys(512)
            keys = {'public': public, 'private': private} 
        

        while True:
            connection, info = server_socket.accept()
            client_thread = threading.Thread(target=client_handler, args=(connection, info, keys))
            client_thread.start()

    except Exception as exc:
        print(exc)
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
    

def client_handler(given_socket:socket.socket, info:tuple, keys):
    'Handle each connection to server'

    try:
        print(f'Client {info[0]}:{info[1]} Connected.')
        if len(keys) > 0:
            send_public_key(given_socket, keys['public'])
            client_public_key = recv_public_key(given_socket)
            print(client_public_key)

        result = True
        while result:
            if len(keys) > 0:
                result = recv_and_proccess(given_socket, keys['private'], client_public_key)
            else:
                result = recv_and_proccess(given_socket)

    except Exception as exc:
        print(exc)
        given_socket.shutdown(socket.SHUT_RDWR)
        given_socket.close()

def createSocket(host:str, port:int, timeout:float):
    '''Creates a TCP socket with given host and port
       Returns if the socket creation was successful
       and created socket/exception'''

    try:
        created_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        created_socket.settimeout(timeout)
        created_socket.connect((socket.gethostbyname(host), port))
        return True, created_socket
    except Exception as exc:
        created_socket.close()
        return False, exc
        

def establish_connection(host:str, port:int, timeout:int) -> socket.socket or None:
    print(f'Trying to connect to {host}:{port}...')
    res, created_socket = createSocket(host, port, timeout)
    if res:
        try:
            print('Connection established.\nWaiting for server...')
            print('DONE! Go ahead')
            return created_socket
        except Exception as exc:
            print(exc)
            return None
    else:
        print(created_socket)
        return None


def send_public_key(given_socket:socket.socket, key):

    encoded_message = pickle.dumps(key)
    encoded_message = encoded_message + b'\r\n'
    message_length = len(encoded_message)
    total_sent = 0
    retry = MAX_RETRY

    while total_sent < message_length and retry > 0:
        try:
            sent_len = given_socket.send(encoded_message[total_sent:])
        
        except socket.timeout:
            retry -= 1
            continue
        
        except Exception as exc:
            print(f'Something went wrong...\n{exc}\nTry again!')
            given_socket.close()
            total_sent += sent_len
            return False
        
        total_sent += sent_len

    return total_sent == message_length


def recv_public_key(given_socket:socket.socket):

    full_text = b''
    while b'\r\n' not in full_text:
        full_text += given_socket.recv(CHUNK_SIZE)

    return  pickle.loads(full_text.split(b'\r\n')[0])

def send_message(given_socket:socket.socket, message:str, public_key=None):
    '''Send the message into the given socket
       Returns total bytes sent'''

    encoded_message = message.encode(ENCODING) if not public_key else rsa.encrypt(message.encode(ENCODING), public_key)
    if LOG_MODE:
        print("Here's what's on this socket!")
        print(encoded_message)
    
    message_length = len(encoded_message)
    total_sent = 0
    retry = MAX_RETRY

    while total_sent < message_length and retry > 0:
        try:
            sent_len = given_socket.send(encoded_message[total_sent:])
        
        except socket.timeout:
            retry -= 1
            continue
        
        except Exception as exc:
            print(f'Something went wrong...\n{exc}\nTry again!')
            given_socket.close()
            total_sent += sent_len
            return False
        
        total_sent += sent_len

    return total_sent == message_length


def send_message_to_host(given_socket:socket.socket, public_key=None, client_private_key=None):
    '''Recieve message from input
       send message nad recieve results'''

    try:
        inputs = get_multi_line_input()
        success = send_message(given_socket, inputs, public_key)

        if not success:
            print('Could not transmit message.')
            return False

        print('\nWaiting for server...')
        msg = recv_message(given_socket, client_private_key)
        print(msg, end='')
        print('Server response recieved!')
        return True

    except Exception as e:
        given_socket.close()
        print(e)
        return False
        

def recv_message(given_socket:socket.socket, private_key=None):
    '''Read content of socket until time out occurs
       Returns the decoded read data'''

    full_text = b''
    while True:
        try:
            data = given_socket.recv(CHUNK_SIZE)
            if not data:
                break
            full_text += data
        except socket.timeout:
            break
        except Exception as exc:
            print(exc)
            break

    if LOG_MODE:
        print('Here is what is on socket!')
        print(full_text)

    if private_key:
        return rsa.decrypt(full_text, private_key).decode(ENCODING)
    else:
        return full_text.decode(ENCODING)


def recv_and_proccess(given_socket:socket.socket, private_key=None, client_public_key=None):
    '''Recieve messages and echo it back
       Execute commands echo back result
       Upload and download files'''

    try:
        first_run = ''
        
        while not first_run:
            first_run = given_socket.recv(CHUNK_SIZE).decode(ENCODING)

        if first_run.startswith('upload'):
            name = first_run.replace('upload', '').replace(' ', '')
            result = recv_file(given_socket, name)
            send_message(given_socket, f'[Server response] Recieved {result} bytes.\n')
            return True

        elif first_run.startswith('exec'):
            out, err = exec_command(first_run[len('exec '):])
            send_message(given_socket, f'[Server response]\nOutput:\n{out.decode(ENCODING)}\nError:\n{err}\n')
            return True

        elif first_run.startswith('download'):
            path = first_run.replace('download', '').replace(' ', '')
            send_file(given_socket, path)
            return True

        elif first_run == 'quit':
            send_message(given_socket, f'[Server response] Disconnecting...\n')
            given_socket.close()
            return False
        
        else:
            got_message = ''
            if private_key:
                while not got_message:
                    got_message = rsa.decrypt(given_socket.recv(CHUNK_SIZE), private_key).decode(ENCODING)
            else:
                while not got_message:
                    got_message = given_socket.recv(CHUNK_SIZE).decode(ENCODING)
            
            print(got_message)
            message = f'[Server response] Got {len(got_message)} bytes of your message.\n'

            if private_key:
                send_message(given_socket, message, client_public_key)
            else:
                send_message(given_socket, message)
            
            return True

    except Exception as exc:
        print(exc)


def exec_command(command:str):
    'Execute given command in server terminal'
    result = subprocess.run(command.split(' '), stdout=subprocess.PIPE)
    return result.stdout, result.stderr


def send_file(given_socket:socket.socket, path:str):
    '''Read file from path
       Send file name
       Send content of file as binary data
       Returns total bytes sent or error'''

    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        send_message(given_socket, str(size) + (CHUNK_SIZE - len(str(size)))* ' ')
        retry = MAX_RETRY

        while retry > 0:
            data = f.read(CHUNK_SIZE)
            if len(data) == 0:
                break
            total_sent = 0
            while total_sent < len(data):
                try:
                    sent_len = given_socket.send(data)

                except socket.timeout:
                    retry -= 1
                    continue
                
                except Exception as exc:
                    print(f'Something went wrong...\n{exc}\nTry again!')
                    given_socket.close()
                    total_sent += sent_len
                    return False
                
                total_sent += sent_len
                print(f'Sent {sent_len}')

        f.close()
        return retry > 0


def recv_file(given_socket:socket.socket, name: str):
    'Read file name and content from socket'

    total_size = 0
    file_size = int(given_socket.recv(CHUNK_SIZE).decode(ENCODING).replace(' ', ''))
    with open(name, 'wb') as f:
        while file_size > total_size:
            data = given_socket.recv(CHUNK_SIZE)
            f.write(data)
            print(f'Recieved {len(data)}')
            total_size += len(data)
        f.close()
        return(total_size)
    


def check_port(host_ip:str, port:int):
    '''Call create_socket check if connection was refused
       Returns if connection was refused'''
    
    res, s = createSocket(host_ip, port, 0.5)
    if type(s) == socket.socket:
        s.close()
    return res


def scan_ports(host_ip_start:str, host_ip_end:str):
    '''Scans over the range of IPs given through port 0 to 1024
       Calls check_port to see if connection is refused
       Prints the open ports of different IPs'''
    
    ip_start = ipaddress.IPv4Address(host_ip_start)
    ip_end = ipaddress.IPv4Address(host_ip_end)

    print('IP\t\tPort\tName\t\tComment\n')
    while ip_start <= ip_end:
        for port in range(1,1024):
            print(f"{round((port*100/1024), 1)}% completed")
            if check_port(str(ip_start), port):
                print ("\033[A                             \033[A")
                name = PORTS_DIC[str(port)]["name"] if str(port) in PORTS_DIC else ""
                comment = PORTS_DIC[str(port)]["comment"] if str(port) in PORTS_DIC else ""
                print(f'{ip_start}\t{port}\t{name}\t\t{comment}\n')
            else:
                print ("\033[A                             \033[A")
        ip_start += 1


def get_multi_line_input():
    '''Gets input multiple times until user inputs done
       Returns the joined values by \r\n'''

    all_inputs = []
    while True:
        recent_input = input()
        if recent_input == 'done':
            all_inputs.append('')
            return '\r\n'.join(all_inputs)
        all_inputs.append(recent_input)


def connect_to_database():
    'Get user and pass and connect to database'

    try:
        db_user = input('Username: ')
        db_password = getpass('Password: ')
        connection = pg.connect(user=db_user,password=db_password,host="127.0.0.1",port="5432",database="telnet_history")

        connection.cursor().execute('''CREATE TABLE IF NOT EXISTS history(
                                        command_id SERIAL PRIMARY KEY,
                                        used_date TEXT,
                                        command TEXT
                                    );''')
        connection.commit()
    
    except Exception as exc:
        print(f'Database {exc}')

    return connection

def add_history(connection, command: str):
    'Insert command in database'

    try:
        cursor = connection.cursor()
        cursor.execute('''INSERT INTO history (used_date, command) VALUES (%(date_time)s,
                       %(command)s);''', {'date_time': str(datetime.now()), 'command': command})
        connection.commit()
    except Exception as exc:
        print(f'Database {exc}')


def get_history(connection):
    'Select and read data from database'

    try:
        result = pd.read_sql_query('SELECT * FROM history', connection)
        print(pd.DataFrame(result).to_markdown())
    except Exception as exc:
        print(f'Database {exc}')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    main()