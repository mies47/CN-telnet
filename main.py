import os
import socket
import sys
import ipaddress
import json

ENCODING = 'utf-8'
CHUNK_SIZE = 1024
PORTS_FILE = open('ports.json', 'r')
PORTS_DIC = json.load(PORTS_FILE)
PORTS_FILE.close()


def main():
    'Main method'
    pass

def createSocket(host:str, port:int):
    '''Creates a TCP socket with given host and port
       Returns if the socket creation was successful
       and created socket/exception'''

    try:
        created_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        created_socket.connect((socket.gethostbyname(host), port))
        created_socket.settimeout(1)
        return True, created_socket
    except Exception as exc:
        created_socket.close()
        return False, exc
        
    
def sendMessage(given_socket:socket, message:str):
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

def sendFile(given_socket:socket, path:str):
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

def check_port(host_ip:str, port:int):
    '''Call create_socket check if connection was refused
       Returns if connection was refused'''
    
    res, s = createSocket(host_ip, port)
    if type(s) == socket.socket:
        s.close()
    return res

def scan_ports(host_ip_start:str, host_ip_end:str):
    '''Scans over the range of IPs given through port 0 to 1024
       Calls check_port to see if connection is refused
       Prints the open ports of different IPs'''
    
    ip_start = ipaddress.IPv4Address(host_ip_start)
    ip_end = ipaddress.IPv4Address(host_ip_end)

    print('IP\t\tPort\tName\t\tComment')
    while ip_start < ip_end:
        for port in range(1024):
            if check_port(str(ip_start), port):
                print(f'{ip_start}\t{port}\t{PORTS_DIC[str(port)]["name"]}\t\t{PORTS_DIC[str(port)]["comment"]}')
        ip_start += 1


if __name__ == '__main__':
    main()