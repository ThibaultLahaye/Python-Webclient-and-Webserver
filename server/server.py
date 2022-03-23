import datetime
import os
import socket
import sys
import threading
import logging
import mimetypes

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

def connection_handler(client_connection, threadID, mode):
    """
    Client connection handler function.
    It handles incomming requests and generated appriopriate responses
    """

    # Start time of the thread
    stime = datetime.datetime.now()
    logging.info(f"Thread-{threadID} - Start Time: {stime}")
    while True:
        try:
            logging.info(f"Thread-{threadID} - receiving_1")
            request = b""
            while True:
                request += client_connection.recv(2024)
                if b'\r\n\r\n' in request:
                    break
            request = request.decode()
            loggin.info(f"Thread-{threadID} - received_1", request)

            if request == '\r\n\r\n':
                break
                logging.info(f"Thread-{threadID} - Connection break")

            # if mode is 500 then always show internal server error
            if mode == 500:
                response = generate_5xx_response(error='configuration')
                client_connection.sendall(response)
                logging.error(f"Thread-{threadID} - Configuration File Error")
                break

            # Check the request format - returns false if its wrong
            # Check if method is GET,PUT,etc
            # Check if http version is specified
            # Some error handeling is done in the generate_xxx_response methods
            status, error = check_request(request)
            logging.debug(f"Thread-{threadID} - check_request_line - {status}, {error}")
            if error:
                if status == '4xx':
                    logging.debug(f"Thread-{threadID} - generate_4xx_response")
                    http_response = generate_4xx_response(error)
                elif status == '5xx':
                    logging.debug(f"Thread-{threadID} - generate_5xx_response")
                    http_response = generate_5xx_response(error)
                else:
                    raise NotImplemented
                    logging.error(f"Thread-{threadID} - Not Implemented")

                client_connection.sendall(http_response)
                break

            method, path, version = request.splitlines()[0].split()
            keep_alive = check_for_keep_alive(request)
            logging.debug(f"Thread-{threadID} - method, path, version - {method} {path} {version}")
            logging.debug(f"Thread-{threadID} - keep_alive - {keep_alive}")

            if method == 'GET':
                logging.info(f"Thread-{threadID} - generate_get_response")
                response = generate_get_response(method, path, keep_alive, threadID)
            elif method == 'HEAD':
                logging.info(f"Thread-{threadID} - generate_head_response")
                response = generate_head_response(method, path, keep_alive, threadID)
            elif method == 'POST':
                logging.info(f"Thread-{threadID} - POST - receiving_2")
                post_data = ""
                while True:
                    post_data += client_connection.recv(2024).decode()
                    if '\r\n\r\n' in post_data:
                        break

                logging.info(f"Thread-{threadID} - POST - post_data", post_data)

                response = generate_post_response(method, path, keep_alive, post_data, threadID)
            elif method == 'PUT':
                logging.info(f"Thread-{threadID} - PUT - receiving_2")
                put_data = ""
                while True:
                    put_data += client_connection.recv(2024).decode()
                    if '\r\n\r\n' in put_data:
                        break

                logging.info(f"Thread-{threadID} - PUT - put_data", put_data)
                response = generate_put_response(method, path, keep_alive, put_data, threadID)
            else:
                raise NotImplementedError

            if keep_alive:
                client_connection.setblocking(True)

                # Get timeout value from configuration file
                client_connection.settimeout(float(_ENVCONFIG['KeepaliveTime']))

                client_connection.sendall(response)
            else:
                client_connection.sendall(response)
                break

        except socket.timeout:
            # timeout occurred after the last keep alive message
            # Time to close the socket and kill the thread
            logging.info(f"Thread-{threadID} - Socket Timeout")
            client_connection.close()
            break
        except ValueError as e:
            logging.error(f"Thread-{threadID} - Exception caught - {e}")
        except Exception as e:
            print("debug ", e)

    # Thread execution is stopping after this
    etime = datetime.datetime.now()
    logging.info("Thread-%d - End Time: %s" % (threadID, str(etime)))
    rtime = etime - stime
    datetime.timedelta(0, 8, 562000)
    logging.info("Thread-%d - Run Time: %s" % (threadID, str(rtime)))

    # if connection was not closed anywhere above then it will be closed here
    print("Connection was not closed anywhere above")
    client_connection.close()

    # return to kill the thread
    # there are other ways to do this
    return False


def generate_get_response(method, path, keep_alive, threadID):
    """
    Generates HTTP GET Response
    It will properly set the keep alive flag or connection close flag as required
    """

    if not path or path == "/":
        # If path is empty, that means user is at the homepage
        # so just serve index.html
        fullpath = _ENVCONFIG["DocumentRoot"] + "/" + "index.html"
    else:
        fullpath =  _ENVCONFIG["DocumentRoot"] + path

    if os.path.isfile(fullpath):

        with open(fullpath, 'rb') as f:
            data = f.read()

        size = len(data.strip())
        # If keep alive was received from the client then we need to return response with keepalive
        if keep_alive:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: keep-alive\r\n',
                                        f'\r\n']).encode()

        else:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: close\r\n',
                                        f'\r\n']).encode()

    # if file was not found in document root then return a 404 not found response
    else:
        response_headers = ''.join([f'HTTP/1.1 404\r\n',
                                    f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                    f'Content-Type: {get_content_type(fullpath)}\r\n',
                                    f'Connection: close\r\n',
                                    f'\r\n']).encode()

        data = b"<html><body> <b>Ops, File Not Found</b> </body> </html>"

    return (response_headers + data)


def generate_head_response(method, path, keep_alive, threadID):
    """
    Generates HTTP HEAD Response
    It will properly set the keep alive flag or connection close flag as required
    """

    if not path or path == "/":
        # If path is empty, that means user is at the homepage
        # so just serve index.html
        fullpath = _ENVCONFIG["DocumentRoot"] + "/" + "index.html"
    else:
        fullpath =  _ENVCONFIG["DocumentRoot"] + path

    if os.path.isfile(fullpath):

        data = b""
        size = len(data.strip())

        # If keep alive was received from the client then we need to return response with keepalive
        if keep_alive:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: keep-alive\r\n',
                                        f'\r\n']).encode()

        else:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: close\r\n',
                                        f'\r\n']).encode()

    # if file was not found in document root then return a 404 not found response
    else:
        response_headers = ''.join([f'HTTP/1.1 404\r\n',
                                    f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                    f'Content-Type: {get_content_type(fullpath)}\r\n',
                                    f'Connection: close\r\n']).encode()

        data = b"<html><body> <b>Ops, File Not Found</b> </body> </html>"

    return (response_headers + data)


def generate_put_response(method, path, keep_alive, put_data, threadID):
    """
    Function to return HTTP reponse for POST request
    It will return post data to path received in the POST request
    This function will also take care of the keep alive flag
    """

    data = b""
    fullpath = _ENVCONFIG["DocumentRoot"] + path

    if not os.path.isfile(fullpath):

        with open(fullpath, 'w') as f:
            f.write(put_data)



        size = len(put_data)
        # If keep alive was received from the client then we need to return response with keepalive
        if keep_alive:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: keep-alive\r\n',
                                        f'\r\n']).encode()

        else:
            response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: close\r\n',
                                        f'\r\n']).encode()

    # If a file already exists
    else:
            response_headers = ''.join([f'HTTP/1.1 404\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Connection: close\r\n',
                                        f'\r\n']).encode()

            data = b"<html><body> <b>File Already Exists</b> </body> </html>"

            return (response_headers + data)

    return (response_headers + data)


def generate_post_response(method, path, keep_alive, post_data, theadID):
    """
    Function to return HTTP reponse for POST request
    It will return post data to path received in the POST request
    This function will also take care of the keep alive flag
    """

    data = b""
    if method == "POST":
        fullpath = _ENVCONFIG["DocumentRoot"] + path
        if os.path.isfile(fullpath):

            # Return a HTML page with post data in it
            # This is hard coded for now but could be automated depending on the use
    #         data = b"""
    # <!DOCTYPE html>
    # <html lang="en">
    # <head>
    #     <meta charset="UTF-8">
    #     <title>Testing Post</title>
    # </head>
    # <body>
    #     <h2>Enter Data to test POST Request</h2>
    #     <form method="post" action="/testpost.html">
    #         <input type="text" name="planetName" required placeholder="Enter Planet Name">
    #         <input type="submit" name="submit" value="submit">
    #     </form>
    # <h1> Post Data </h1>
    # <pre>
    # """ + post_data + b"""
    # </pre>
    # </body>
    # </html>
    # """

            print("fullpath: ", fullpath)
            print("post_data type: ", type(post_data))
            try:
                with open(fullpath, 'w') as f:
                    f.write(post_data)
            except:
                print("write to file error")

            size = len(post_data)
            # If keep alive was received from the client then we need to return response with keepalive
            if keep_alive:
                response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: keep-alive\r\n',
                                        f'\r\n']).encode()

            else:
                response_headers = ''.join([f'HTTP/1.1 200 OK\r\n',
                                        f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                        f'Content-Type: {get_content_type(fullpath)}\r\n',
                                        f'Content-Length: {size}\r\n',
                                        f'Connection: close\r\n',
                                        f'\r\n']).encode()

                # if file was not found in document root then return a 404 not found response
        else:
            response_headers = ''.join([f'HTTP/1.1 404\r\n',
                                    f'Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n',
                                    f'Content-Type: {get_content_type(fullpath)}\r\n',
                                    f'Connection: close\r\n']).encode()

            data = b"<html><body> <b>Ops, File Not Found</b> </body> </html>"

    return (response_headers + data)


def generate_5xx_response(error):
    """
    Function to return html page for 500 error
    """
    response_headers = ""
    data = b""
    if error == 'configuration':
        response_headers = b"HTTP/1.1 500 Internal Server Error\nConnection: close\n\r\n"
        data = b"<html><body> <h1> Internal Server Error: Configurtation Error</h1> </body> </html>"
    elif error == 'HTTP version not supported':
        response_headers = b"HTTP/1.1 505 Internal Server Error\nConnection: close\n\r\n"
        data = b"<html><body> <h1> Internal Server Error: HTTP version not supported</h1> </body> </html>"
    else:
        print("generate_5xx_response - not implemented")
        raise NotImplemented

    return (response_headers + data)


def generate_4xx_response(error):
    """
    Function to return html page for 400 error
    Function will return appropriate html for type of error
    """

    data = b""
    if error == "invalid method":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason: Invalid Method :<<request method>></body></html"
    elif error == "invalid uri":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason: Invalid URL: <<requested url>></body></html>"
    elif error == "bad request":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason<<requested url>></body></html>"
    elif error == "method not implemented":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason: Method not implemented: <<requested url>></body></html>"
    elif error == "host not specified":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason: Host not specified or specified incorrectly: <<requested url>></body></html>"
    elif error == "content-length not specified":
        response_headers = ''.join([f"HTTP/1.1 400\r\n",
                                    f"Connection: close\r\n"]).encode()

        data = b"<html><body>400 Bad Request Reason: Connection-Length not specified or specified incorrectly: <<requested url>></body></html>"
    else:
        print("generate_4xx_response - not implemented")
        raise NotImplemented

    return (response_headers + data)


def check_request(request):
    """
    Check request line format
    Check list -
    1. Method
    2. URI format
    3. HTTP version
    """

    try:
        #########################
        # Checking Request Line #
        #########################
        try:
            request_line = request.splitlines()[0]
            method, url, ver = request_line.split()
        except:
            return "4xx", "bad request"

        logging.debug(f'check_requets_line - {method}, {url}, {ver}')
        methods = "GET,OPTIONS,HEAD,POST,PUT,DELETE,TRACE"

        # Check if the method is a valid http method
        if method not in methods.split(','):
            return "4xx", "invalid method"

        # Check if the method is implemented
        if not valid_request_method(method):
            return '4xx', "method not implemented"

        # Check if the URI startes with /
        # There could be some more checks for example:
        # IE does not allow ":" in URI
        if url[0] != "/":
            return '4xx', "invalid uri"

        # This server supports only HTTP/1.1
        # Anything other than those will be considered as in valid request
        if repr(ver).strip() != repr('HTTP/1.1'):
            return '5xx', "HTTP version not supported"

        ####################
        # Checking Headers #
        ####################

        print("check_for_host: ", check_for_host(request))

        if not check_for_host(request):
            return '4xx', 'host not specified'

        if method == 'POST' or method== 'PUT':
            if not check_for_content_length(request):
                return '4xx', 'content-length not specified'

        return None, None
    except ValueError:
        logging.error('check_request_line - error')


def valid_request_method(method):
    """
    Function to check if the request is implemented on the webserver
    Implemented methods are set with the RequestMethodSupport directive in configuration file
    """
    try:
        supportedmethods = _ENVCONFIG['RequestMethodSupport']
        if len(supportedmethods) > 1:
            if method not in supportedmethods.split(','):
                return False
        else:
            if method != supportedmethods:
                return False
    except ValueError:
        pass

    return True


def check_for_keep_alive(request):
    """
    Function for determining wheater or not to keep the connection alive.
    HTTP/1.1 default is to keep the connection alive until the 'Connection':'close' header is specified
    or until the connection timeout is reached.
    """
    try:
        # Need to parse the whole request as the keep alive flag is not always on 6th position
        # Different could browsers send it in different formats
        for r in request.splitlines():
            print(r)
            if 'Connection:' in r:
                conn_option = r.split(':')[1]

                if conn_option.strip().lower() == 'keep-alive' or conn_option.strip().lower() == 'keepalive':
                    return True

                if conn_option.strip().lower() == 'close':
                    return False

    except ValueError:
        pass

    # HTTP/1.1 default uses persistent connections
    # return None
    return True


def check_for_host(request):
    """
    The server should respond with the “400: Bad Request” status code when the HTTP
    Client does not include the host header in its request for HTTP version 1.1.
    """
    print("check_for_host")
    try:
        # Need to parse the whole request as the keep alive flag is not always on 6th position
        for r in request.splitlines():
            print(r)
            if 'Host:' in r:
                host_value = r.split(':')[1]

                if host_value.strip() == _ENVCONFIG["ServerIP"]:
                    return True

    except ValueError:
        print("check_for_host - error")

    return False


def check_for_content_length(request):
    """
    The server should respond with the “400: Bad Request” status code when the HTTP
    Client does not include the host header in its request for HTTP version 1.1.
    """
    print("check_for_content_lenght")
    try:
        # Need to parse the whole request as the keep alive flag is not always on 6th position
        for r in request.splitlines():
            print(r)
            if 'Content-Length' in r:
                content_length_value = r.split(':')[1]

                if int(content_length_value.strip()) > 0:
                    return True

    except ValueError:
        print("check_for_content_length - error")

    return False


def get_content_type(path):
    """
    Function to return content type from the global configuration dict
    If content-type was not found the return False
    """
    try:
        http_response_header_contenttype = mimetypes.guess_type(path)[0] or 'text/html'
    except KeyError:
        http_response_header_contenttype = False

    return http_response_header_contenttype


def start_webserver(mode):
    """
    Main function of the Webserver.
    Listens for incomming connections and handles them in seperate threads.
    """
    try:
        ServerIP = _ENVCONFIG['ServerIP']
        ServerPort = int(_ENVCONFIG["ListenPort"])

        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind((ServerIP, ServerPort))

        # Accept 50 backlog connections in the queue
        # Not required as we are using threading
        listen_sock.listen(50)
        logging.info(f'Serving HTTP on port {ServerPort} ...')
        print(f'Serving HTTP on port {ServerPort} ...')
        print(f'Check server.log for more information')

        id = 1
        while True:
            # Accept new request from clients
            # Blocking Statement
            client_connection, client_address = listen_sock.accept()

            # Create a new thread for every request
            # id - program generated thread id
            # mode = 500 when there is configuration file error
            thread = threading.Thread(target=connection_handler, args=(client_connection, id, mode))

            # start function will start the execution of the handler function
            thread.start()
            id += 1
    except ValueError as e:
        logging.error(e)
        logging.error("Something went wrong!")
        sys.exit(0)
    except KeyError as e:
        logging.error("Missing Configuration " + str(e))
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info("Closing Socket and Exiting Server Gracefully...")
        print("Closing Socket and Exiting Server Gracefully...")
        listen_sock.close()
        sys.exit(0)


def read_config():
    """
    Function to read the configuration file and create a global DIC
    This function will also check for any mis-configuration in the file
    and set the mode flag as 500 due to which the server will always show
    500 Internal server error
    """
    if _CONFIGURATION_FILE and os.path.isfile(_CONFIGURATION_FILE):

        # Clear any data that might be in the dict
        _ENVCONFIG.clear()

        # Open the configuration file
        fh = open(_CONFIGURATION_FILE)
        content = fh.read().splitlines()

        for line in content:

            # ignore comments
            if line[0] != "#":
                try:
                    if line.split()[0] == "DocumentRoot":
                        (var_name, value) = line.split()
                        if not value:
                            raise ValueError
                        _ENVCONFIG[var_name] = value.strip('"')
                    elif line.split()[0] == "DirectoryIndex":
                        splitted = line.split()
                        if len(splitted) < 2:
                            raise ValueError
                        var_name = splitted[0]
                        valpack = []
                        for i in range(1, len(splitted)):
                            valpack.append(splitted[i])
                        _ENVCONFIG[var_name] = valpack
                    elif line.split()[0] == "ContentType":
                        (var_name, value1, value2) = line.split()
                        _ENVCONFIG[var_name + " " + value1] = value2
                    elif line.split()[0] == "ListenPort":
                        (var_name, value) = line.split()
                        if not value:
                            raise ValueError
                        if int(value) < 1024:
                            logging.error("Error: WebServer Can not start on ports < 1024\nError: Update ListenPort in configuration file")
                            sys.exit(0)
                        _ENVCONFIG[var_name] = value.strip('"')
                    else:
                        (var_name, value) = line.split()
                        if not value:
                            raise ValueError
                        _ENVCONFIG[var_name] = value.strip('"')

                # Catch any split error
                # This is used to check mis-configuration in the configuration file
                except ValueError:
                    return False
    else:
        logging.error("Error: Set configuration file not present\nError: Exiting the server ...")
        sys.exit(0)

    return True


if __name__ == "__main__":
    # Check the config file
    # Status 500 - If there is an error in the server configuration
    if not read_config():
        start_webserver(mode=500)
    else:
        # GenerateFiles(100)
        start_webserver(mode=1)
