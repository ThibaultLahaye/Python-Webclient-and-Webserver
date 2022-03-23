import datetime
import os
import socket
import sys
import threading
import logging
import mimetypes
import time

from bs4 import BeautifulSoup
import re

# Logging Configuration
logging.basicConfig(
    format='%(levelname)s:%(message)s',
    filename='server.log',
    encoding='utf-8',
    filemode='w',
    level=logging.DEBUG)

# Configuration File Name
_CONFIGURATION_FILE = "ws.conf"

# Global DICT to store server configuration directives
_ENVCONFIG = {}


def start_webclient():
    method = 'GET'
    uri = 'http://www.google.com'
    port = 80

    protocol, host, path = parse_uri(uri)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    connection_handler(client_socket, method, protocol, host, port, path)


def connection_handler(client_socket, method, protocol, host, port, path):
    """
    Webserver connection handler function.
    It handles connecting to a webserver and sending the appropriate requests
    """
    data = 'test 4+684894sd564f8sdf4qd89s456+f4dsqf4d89q4f6sd54f56ds489e4fs564df89es4r64df8e89s4f8sfe566s4d5f64s8sef86s4d5fe89sf4e86fs45d64e89sf4e894fs6fd456fes8f4ds6fe8sf4sd654f894'

    extra_headers = ""
    if method == 'GET':
        request = generate_get_request(host, path, extra_headers)
    elif method == 'HEAD':
        request = generate_head_request(host, path)
    elif method == 'POST':
        request = generate_post_request(host, path, data=data)
    elif method == 'PUT':
        request = generate_put_request(host, path, data=data)
    else:
        raise NotImplemented

    print('Sending request')
    print(request)
    client_socket.sendall(request)

    print('Receiving response')
    header = recv_header(client_socket)
    print("header", header)

    response = recv_body(client_socket, header)
    # print("body", response)

    try:
        download_embedded_images(client_socket, response, protocol, host, port, path, response)
    except Exception as e:
        print(e)


def generate_get_request(host, path, extra_headers={}):

    request_headers = ''.join([f'GET {path} HTTP/1.1\r\n',
                               f'Host: {host}\r\n',
                               f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                               # f'Content-Length: {size}\r\n',
                               f'Connection: keep-alive\r\n',
                               f'\r\n']).encode()

    for header in extra_headers:
        request_headers += f'{header}: {extra_headers[header]}\r\n'

    return request_headers


def generate_head_request(host, path, extra_headers={}):
    request_headers = ''.join([f'HEAD {path} HTTP/1.1\r\n',
                               f'Host: {host}\r\n',
                               f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                               # f'Content-Length: {size}\r\n',
                               f'Connection: keep-alive\r\n',
                               f'\r\n']).encode()

    for header in extra_headers:
        request_headers += f'{header}: {extra_headers[header]}\r\n'

    return request_headers


def generate_post_request(host, path, extra_headers={}, data=''):
    request_headers = ''.join([f'POST /{path} HTTP/1.1\r\n',
                               f'Host: {host}\r\n',
                               f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                               f'Content-Length: {len(data)}\r\n',
                               f'Connection: keep-alive\r\n',
                               f'\r\n']).encode()

    for header in extra_headers:
        request_headers += f'{header}: {extra_headers[header]}\r\n'

    return request_headers + data.encode() + b"\r\n\r\n"


def generate_put_request(host, path, extra_headers={}, data=''):
    request_headers = ''.join([f'PUT /{path} HTTP/1.1\r\n',
                               f'Host: {host}\r\n',
                               f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                               f'Content-Length: {len(data)}\r\n',
                               f'Connection: keep-alive\r\n',
                               f'\r\n']).encode()

    for header in extra_headers:
        request_headers += f'{header}: {extra_headers[header]}\r\n'

    return request_headers + data.encode() + b"\r\n\r\n"


def parse_uri(uri):
    """
    Method
    """

    if uri[0:7].lower() == "http://":
        protocol = uri[0:7]
        host = uri[7:].split("/")[0]
        path = "/".join(uri[7:].split("/")[1:])

    elif uri[0:8].lower() == "https://":
        protocol = uri[0:8]
        host = uri[8:].split("/")[0]
        path = "/".join(uri[8:].split("/")[1:])

        raise NotImplementedError('Only HTTP/1.1 is supported')

    else:
        protocol = 'http://'
        host = uri.split("/")[0]
        path = "/".join(uri.split("/")[1:])

    if path == '': path = '/'

    return protocol, host, path


def download_embedded_images(client_socket, response, protocol, host, port, path, get_response):
    """
    Method Parses an http response for embedded images. It then generates and sends http requests for them.
    """

    # Bs4 is used to parse the html response
    soup = BeautifulSoup(response, 'html.parser')

    img_tags = soup.find_all(['img', 'image'])
    print('Parsing response for embedded images')
    #print('images: ', img_tags)

    urls = [img['src'] for img in img_tags]
    #print('Parsing image tags for srcs')
    print('Images: ', urls)

    for url in urls:
        if url[0] == '.':
            url = url[1:]

        request = generate_get_request(host, url)

        try:
            client_socket.sendall(request)
        except Exception as e:
            print('Info: ', e)
            print('Opening a new Connection')
            client_socket.close()
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            print('Sending request')
            print(request)
            client_socket.sendall(request)

        print('Receiving response')
        header = recv_header(client_socket)
        print("header", header)

        #response = client_socket.recv(4096000)
        response = recv_body(client_socket, header)
        print("body", response)

        try:
            filename = url.split("/")[-1]

            with open(filename, "wb") as file:
                file.write(response)

        except:
            print("Failed to save image")


def recv_header(sock):
    header = b""
    while True:
        header += sock.recv(1)
        if b'\r\n\r\n' in header:
            break

    return header


def recv_body(sock, header=None):

    content_length = get_content_length(header)
    transfer_encoding = get_transfer_encoding(header)

    body = b''
    if content_length:
        print("case: content-length")
        body_received = b""
        while len(body_received) < content_length:
            body_received += sock.recv(content_length - len(body_received))

        body = body_received

    elif transfer_encoding:
        print("case: transfer-encoding")
        while True:
            print("test")
            block_size = b""
            while True:
                block_size += sock.recv(1)
                if b'\r\n' in block_size:
                    break

            block_size = block_size.split(b'\r\n')[0].strip().decode()
            print("")
            print("block_size", block_size)

            if block_size == '0':
                break

            print("testest")

            try:
                block_size = int(block_size, 16)
            except Exception as e:
                block_size = 0
                print(e)

            block_received = b""
            while len(block_received) < block_size:
                block_received += sock.recv(block_size - len(block_received))

            print("")
            print("received_block", block_received)
            body += block_received

    else:
        print("case: else")
        while True:
            body +=  sock.recv(1024)
            if b'\r\n\r\n' in body:
                break

    return body


def get_transfer_encoding(header):
    """
    """

    try:
        # Need to parse the whole request as the content-length header is not always in the same position
        for r in header.splitlines():
            if b'Transfer-Encoding' in r:
                transfer_encoding_value = r.split(b':')[1]

                return transfer_encoding_value.strip().decode()

    except Exception as e:
        print("get_transfer_encoding - ", e)

    return None


def get_content_length(header):
    """
    """

    try:
        # Need to parse the whole request as the content-length header is not always in the same position
        for r in header.splitlines():
            if b'Content-Length' in r:
                content_length_value = r.split(b':')[1]

                return int(content_length_value.strip().decode())

    except Exception as e:
        print("get_content_length - ", e)

    return None


if __name__ == "__main__":
    # Check the config file
    # Status 500 - If there is an error in the server configuration
    start_webclient()
