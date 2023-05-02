# TELNET Protocol Implementation

This a P2P implementation of telnet. This program transfers data on TCP sockets as plain text.

**This is not a complete implementation in telnet protocol based on [rfc854](https://datatracker.ietf.org/doc/html/rfc854). There is no option negotiation to establish an NVT**

This script could be used for:

1. Sending plain text messages to server
2. Upload and download files to and from a peer
3. Execute commands on another peer and get the results
4. Scan open ports of a host
5. Send other requests such as SMTP or HTTP requests to servers.

This program uses PostgreSQL to save commands entered on client side on telnet_history database. When you run program in client mode it asks for username and password to connect to Postgre database.

You need to run this script as 2 proccesses for client and server mode.

To exit the program press Ctrl+c.

## Server Mode

To run in server mode you need to run the following command in terminal:
```
>python3 main.py server [portnumber]
```
portnumber is the port server is going to listen on.

## Client Mode
To run in client mode you need to run the following command in terminal:
```
>python3 main.py client
```
- To establish a connection:
    ```
    telnet> open [host] [port]
    ```
    When connection is established you can:

    1. Send message to another peer:

        ```
        127.0.0.1:2250> send message
        hi
        done
        ```
    2. Send message to a remote SMTP or HTTP server:

        ```
        google.com:80>send remote
        GET / HTTP/1.1
        HOST: google.com

        done

        Waiting for server...
        HTTP/1.1 301 Moved Permanently
        Location: http://www.google.com/
        Content-Type: text/html; charset=UTF-8
        Date: Sun, 30 May 2021 11:24:52 GMT
        Expires: Tue, 29 Jun 2021 11:24:52 GMT
        Cache-Control: public, max-age=2592000
        Server: gws
        Content-Length: 219
        X-XSS-Protection: 0
        X-Frame-Options: SAMEORIGIN

        <HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
        <TITLE>301 Moved</TITLE></HEAD><BODY>
        <H1>301 Moved</H1>
        The document has moved
        <A HREF="http://www.google.com/">here</A>.
        </BODY></HTML>
        Server response recieved!
        ```
    3. Upload a file to a peer:
        ```
        127.0.0.1:2250> upload [path]
        ```
    4. Download file from a peer:
        ```
        127.0.0.1:2250> download [path]
        ```
    5. Execute a command on peer:
        ```
        127.0.0.1:2250> exec [command]
        ``` 
    6. Disconnect:
        ```
        127.0.0.1:2250> quit
        ``` 
- To scan 1 to 1024 ports from start_ip to end_port:
    ```
    telnet> scan [start_ip] [end_ip]
    ```
- You could also see the previouse commands:
    ```
    telnet> history
    ```
