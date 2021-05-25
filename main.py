import os
import socket
import sys
import ipaddress
import json
import signal
import subprocess

ENCODING = 'utf-8'
CHUNK_SIZE = 1024
PORTS_FILE = open('ports.json', 'r')
PORTS_DIC = json.load(PORTS_FILE)
PORTS_FILE.close()

def main():
    'Main method'

    if len(sys.argv) < 3:
        print('need more args!!')
        sys.exit(-1)

    if(sys.argv[1] == 'scan'):
        scan_ports(sys.argv[2], sys.argv[3])

    elif(sys.argv[1] == 'upload'):
        try:
            res, s = createSocket(sys.argv[3], int(sys.argv[4]), 1)
            if res:
                sendFile(s, sys.argv[2])
        except Exception as exc:
            s.close()
            print(exc)
            sys.exit(-1)
    
    else:
        res, s = createSocket(sys.argv[1], int(sys.argv[2]), 1)
        if res:
            while True:
                try:
                    print('\nWaiting for server...')
                    msg = recvMessage(s)
                    print(msg, end='')
                    print('DONE! Server response is:\n')
                    inputs = get_multi_line_input()
                    sendMessage(s, inputs)
                except socket.timeout:
                    pass
                except Exception as e:
                    s.close()
                    print(e)
                    sys.exit()
        else:
            print(s)


def sigint_handler(sig, frame):
    'Capture SIGINT signal and exit program'

    print('\nYou pressed Ctrl+C! QUITING...')
    sys.exit(0)


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
        
    
def sendMessage(given_socket:socket.socket, message:str):
    '''Send the message into the given socket
       Returns total bytes sent'''

    encoded_message = message.encode(ENCODING)
    message_length = len(encoded_message)
    total_sent = 0
    while total_sent < message_length:
        try:
            sent_len = given_socket.send(encoded_message[total_sent:])
        except:
            print('Something went wrong on socket transmission...')
            given_socket.close()
            total_sent += sent_len
            return total_sent
        finally:
            total_sent += sent_len
    return total_sent


def recvMessage(given_socket:socket.socket):
    '''Read content of socket until time out occurs
       Returns the decoded read data'''

    full_text = ''
    while True:
        try:
            data = given_socket.recv(CHUNK_SIZE)
            if data == b'\xff\x00':
                return 'File'
            if not data:
                return full_text
            full_text += data.decode(ENCODING)
        except:
            return full_text

def execCommand(command:str):
    'Execute given command in my terminal'
    result = subprocess.run(command, stdout=subprocess.PIPE)
    return result.stdout, result.stderr


def sendFile(given_socket:socket.socket, path:str):
    '''Read file from path
       Send 16bits to specify file transfer(\xff\x00)
       Send file name
       Send content of file as binary data
       Returns total bytes sent or error'''

    with open(path, 'rb') as f:
        fileName = os.path.basename(path)
        given_socket.send(b'\xff\x00') #Sending some random bits. I hope it works.
        given_socket.send(fileName.encode(ENCODING))

        while True:
            data = f.read(CHUNK_SIZE)
            if len(data) == 0:
                break
            total_sent = 0
            while total_sent < len(data):
                try:
                    sent_len = given_socket.send(data)
                except:
                    print('Something went wrong on socket transmission...')
                    given_socket.close()
                    total_sent += sent_len
                    return total_sent
                finally:
                    total_sent += sent_len

        f.close()


def recvFile(given_socket:socket.socket):
    '''Read file name and content from socket
       If the first 16bits are \xff\x00'''

    data = given_socket.recv(1024)
    name = data.decode('utf-8')
    with open(name, 'wb') as f:
        while True:
            data = given_socket.recv(1024)
            if not data:
                break
            f.write(data)
        f.close()


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


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    main()