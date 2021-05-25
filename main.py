import os
import socket
import sys

ENCODING = 'utf-8'
CHUNK_SIZE = 1024

def main():
    'Main method'
    pass

def createSocket(host:str, port:int):
    '''Creates a TCP socket with given host and port
       Returns the created socket'''
    try:
        created_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        created_socket.connect((socket.gethostbyname(host), port))
        created_socket.settimeout(1)
        return created_socket
    except Exception as exc:
        print(exc)
        created_socket.close()
        sys.exit(-1)
    
def sendMessage(given_socket:socket, message:str):
    '''Send the message into the given socket
       Returns total bytes sent'''
    encoded_message = message.encode(ENCODING)
    message_length = len(encoded_message)
    total_sent = 0
    given_socket.send('MESG'.encode(ENCODING))
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
    '''Read file from path and send it via socket
       Returns total bytes sent or error'''
    with open(path, 'rb') as f:
        fileName = os.path.basename(path)
        given_socket.send('FILE'.encode(ENCODING))
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
                    pass
                finally:
                    total_sent += sent_len

        f.close()



    


if __name__ == '__main__':
    main()