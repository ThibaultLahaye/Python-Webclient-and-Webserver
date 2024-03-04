# Python webclient & webserver

## Introduction
The goal of this project is to gain experience in application layer network programming through [Python Sockets](https://docs.python.org/3/library/socket.html) and get familiarized with the basics of distributed programming. Specifically, this project will help to understand the [Hypertext Transfer Protocol (HTTP)](https://en.wikipedia.org/wiki/HTTP), which is one of the most widely used protocols on the Internet, and the operation of webpage translators. 

## Project Description
Specifically, this project focusess on inplementing a subset of the [HTTP/1.1](https://datatracker.ietf.org/doc/html/rfc2616) protocol. Two major components have been written, a webclient and webserver, described below.

[HTTP/1.1](https://datatracker.ietf.org/doc/html/rfc2616) introduced several key improvements over [HTTP/1.0](https://datatracker.ietf.org/doc/html/rfc1945). These include __persistent connections__, inplemented in the client & server, allowing multiple requests and responses over a single TCP connection, reducing connection overhead. Additionally, __pipelining__ enables sending multiple requests without waiting for each response. Also, __Chunked transfer encoding__ allows servers to send responses in chunks.

### Client
The `web_client.py` file contains the inmelentation of a simple web client in [python](https://www.python.org/). 

Some of its features:
- __HTTP Request Generation:__ The script can generate various types of HTTP requests such as GET, HEAD, POST, and PUT.
- __Multithreaded:__ It uses threading to handle multiple connections concurrently.
- __Error Handling:__ Includes error handling mechanisms for various scenarios such as connection failures and file writing errors.
- __Supports Keep-Alive:__ Sets the Connection header to keep-alive for persistent connections.
- __Content-Length and Transfer-Encoding Handling:__ Supports parsing of Content-Length and Transfer-Encoding headers for handling response bodies.

### Server
The `web_server.py` file contains the implementation of a simple web server in [Python](https://www.python.org/). It provides basic functionality to handle incoming HTTP requests, serve static files, and generate appropriate HTTP responses.

Some of its features:
- __Connection Handling:__ The server listens for incoming connections and spawns a new thread to handle each connection. (ref. Threading)
- __Request Processing:__ Incoming HTTP requests are processed by the connection_handler function. It parses the request, validates its format, and generates appropriate responses based on the requested method (GET, HEAD, POST, PUT).
- __Response Generation:__ Sends response back the to client based on their request.
- __Content Type Handling:__ The server determines the content type of files based on their extensions using the mimetypes module. 
- __Keep-Alive Support:__ The server supports HTTP keep-alive connections, allowing clients to reuse the same connection for multiple requests if requested.
- __Threading:__ Threading is used to handle multiple connections concurrently, improving the server's efficiency and scalability.
- __Chunked Transfer Encoding__ : 
- __Configuration File Handling:__ The server reads configuration directives from a file named ws.conf. These directives include settings such as the document root directory, supported request methods, content types, and the listening port.
