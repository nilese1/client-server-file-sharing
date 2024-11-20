import socket
import struct
import threading
from threading import Thread
from enum import Enum
import logging
from pathlib import Path
import datetime
import json
from handleFolders import *
from handleFiles import *
import base64
import hashlib
import os
import ssl

# Load or define users and password hashes
user_db = {
    'user1': hashlib.sha256(b'password1').hexdigest(),
    'user2': hashlib.sha256(b'password2').hexdigest()
}

class PacketType(Enum):
    LOGIN = 1
    SEND = 2
    REQUEST = 3
    DISCONNECT = 4
    INVALID = 5

LOG_LEVEL = logging.DEBUG
logging.basicConfig(filename=Path(f'logs/log_{datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")}.log'), level=LOG_LEVEL,
                    format='[%(asctime)s][%(levelname)s]: %(message)s', filemode='w')
logger = logging.getLogger(__name__)
logger.info(f'Beginning log of {__name__}')

# to show log in console feel free to comment out
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s'))
logger.addHandler(console_handler)


BUFFER_SIZE = 4096
MAX_CLIENTS = 10
# read from config file later
HOST = '127.0.0.1'
PORT = 30000

# SSL setup for secure connections
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile="server.crt", keyfile="server.key")  # SSL certificate and key

# Challenge generation for secure authentication
def generate_challenge():
    return os.urandom(16).hex()

def verify_password(challenge, password_hash, received_hash):
    hash_object = hashlib.sha256((password_hash + challenge).encode())
    return hash_object.hexdigest() == received_hash

# So multiple clients can download the same file at the same time
# or download a file currently being uploaded
lock = threading.Lock()


class Server:
    def __init__(self):
        Thread.__init__(self)
        # only client handlers go in here
        self.connected_clients = []

        # start server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(MAX_CLIENTS)
        # so server isn't waiting for connection forever (necessary to exit gracefully) 
        self.server_socket.settimeout(0.1)

    def run(self):
        logger.info(f'Server listening on {HOST}:{PORT}')

        # I know this looks bad but this was the only way I could get this to exit gracefully
        try:
            # listen for connection from client
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    secure_socket = context.wrap_socket(client_socket, server_side=True)
                    logger.info(f'Client from {addr} connected')
                    self.connect_new_client(client_socket, addr)
                except socket.timeout:
                    pass 
                except Exception as e:
                    logger.error(f'Error connecting client {e}')

        except KeyboardInterrupt as e:
            logger.info(f'KeyboardInterrupt detected: Server exiting...')
            

    def connect_new_client(self, client_socket, ip_addr):
        client_handler = ClientHandler(client_socket, ip_addr, self)
        client_handler.start() # check ClientHandler.run()


        self.connected_clients.append(client_handler)

    def disconnect_client(self, client_handler):
        self.connected_clients.remove(client_handler)
        logger.info(f'Client at {client_handler.client_ip} has disconnected')

    def close(self):
        for client in self.connected_clients:
            client.close()
            client.stop()

        self.server_socket.close()


class ClientHandler(Thread):
    def __init__(self, client_socket, client_ip, server):
        Thread.__init__(self)
        self.client_socket = client_socket
        self.client_ip = client_ip
        self.server = server

        self._stop = threading.Event()

        self.client_socket.settimeout(1.0)

    # Given a dict, converts it to a binary json
    def create_packet(self, packet_type, data):
        # packet structure: [id, packet_type, data]
        data_bytes = base64.b64encode(json.dumps(data).encode('utf-8'))
        header = struct.pack('!BI', packet_type.value, len(data_bytes))

        return header + data_bytes
    
    def send_packet(self, packet_type, data):
        try:
            packet = self.create_packet(packet_type, data)
            self.client_socket.send(packet)
            logger.debug(f'Sent packet of type {packet_type} to {self.client_ip}')
        except Exception as e:
            logger.error(f'Unable to send packet: {e}')

    def receive_packet(self):
        try:
            # Read the packet header to get packet type and size
            packet_header = self.client_socket.recv(5)
            if len(packet_header) < 5:
                return None, None, None  # Incomplete header, return None

            # Unpack the header to get the packet type and size of the data payload
            packet_type, packet_size = struct.unpack('!BI', packet_header)

            # Receive the actual data payload based on the packet size
            packet_data_raw = self.client_socket.recv(packet_size)

            # Decode the payload and load it as JSON
            packet_data_str = base64.b64decode(packet_data_raw).decode('utf-8')
            packet_data = json.loads(packet_data_str)  # Ensure packet_data is a dictionary

            return packet_type, packet_size, packet_data
        except Exception as e:
            logger.error(f"Error receiving packet: {e}")
            return None, None, None  # Return None on error for consistent handling
        
    def wait_for_packet(self):
        # Unpack the packet directly and only proceed if we get a valid packet
        packet_type, packet_size, packet_data = self.receive_packet()
        if packet_type is not None and packet_data is not None:
            logger.debug(f"Received packet: type={packet_type}, size={packet_size}, data={packet_data}")
            self.handle_packet(packet_type, packet_size, packet_data)
        else:
            logger.error("Received an invalid or empty packet, skipping packet handling.")

    # runs all the time on the thread
    def run(self):
        try:
            while True:
                if self.stopped():
                    return

                try:
                    self.wait_for_packet()
                except socket.timeout:
                    pass
                # client handler errors on close if this isn't here
                # if another fix is found feel free to change  
                # except Exception as e:
                #     logger.error(f'Error in client handler: {e}')

        except KeyboardInterrupt:
            pass
        finally:
            logger.debug(f'ClientHandler connected to {self.client_ip} stopping...')
            self.close()

    def handle_packet(self, packet_type, packet_size, packet_data):
        if not self.authenticated:
            if packet_type == PacketType.LOGIN.value:
                    self.handle_login_packet(packet_data)
            else:
                    self.send_packet(PacketType.INVALID, {"error": "Authentication required"})
            return
        # Process other packet types if authenticated
        ...
        ...

                # TODO: implement packet handlers
    def handle_invalid_packet(self, size, data):
        logger.error(f'Client from {self.client_ip} has sent an invalid packet.')

    class ClientHandler(Thread):
        def __init__(self, client_socket, client_ip, server):
            super().__init__()
            self.client_socket = client_socket
            self.client_ip = client_ip
            self.server = server
            self.authenticated = False  # Track authentication status

    def handle_login_packet(self, data):
        username = data.get("username")
        received_password_hash = data.get("password")
        stored_password_hash = user_db.get(username)

        if stored_password_hash and received_password_hash == stored_password_hash:
            self.authenticated = True
            self.send_packet(PacketType.LOGIN, {"status": "success"})
            logger.info(f"Client {self.client_ip} authenticated successfully.")
        else:
            self.send_packet(PacketType.INVALID, {"error": "Invalid credentials"})
            logger.info(f"Client {self.client_ip} failed authentication.")


    def handle_send_packet(self, size, data):
        # put a match statement here so we can handle different types of sends (even though we never will)
        match data['type']:
            case 'upload':
                try:
                    logger.info(f'Received upload request for {data["path"]}')

                    packet_data = {'data' : 'not null'}
                    total_bytes_received = 0
                    total_file_size = data['size']
                    if data['path'] == '':
                        data['path'] = data['filename']

                    # receive file data
                    with open(Path(ROOT_PATH) / data['path'], 'wb') as file:
                        # send confirmation packet if it is ok to upload
                        self.send_packet(PacketType.SEND, 'null')

                        while packet_data['data'] != 'null':
                            packet_type, packet_size, packet_data = self.receive_packet()
                            decoded_data = base64.b64decode(packet_data['data'].encode('utf-8'))
                            file.write(decoded_data)
                            total_bytes_received += len(decoded_data)
                    
                    # send confirmation packet
                    self.send_packet(PacketType.SEND, 'null')

                    logger.info(f'Finished uploading file {data["path"]}')
                except Exception as e:
                    logger.error(f'Error uploading file {data["filename"]}: {e}')
                    self.send_packet(PacketType.INVALID, f'Error uploading file {data["filename"]}: {e}')

            case _:
                logger.error(f'Invalid packet subtype received from {self.client_ip}, received subtype {data["type"]}')

    def handle_request_packet(self, size, data):
        match data['type']:
            case 'filetree':
                filetree = list_dir(Path(ROOT_PATH))
                self.send_packet(PacketType.SEND, {
                    'type' : 'filetree',
                    'data' : filetree
                })
            
            case 'delete':
                logger.debug(f'Deleting file {Path(ROOT_PATH) / data["path"]}')
                try:
                    delete_dir(Path(ROOT_PATH) / data['path'])
                    logger.info(f'Deleted file {data["path"]}')
                    self.send_packet(PacketType.REQUEST, 'null')
                except Exception as e:
                    self.send_packet(PacketType.INVALID, f'Error deleting file {data["path"]}: {e}')
                    logger.error(f'Error deleting file {data["path"]}: {e}')

            case 'create_dir':
                try:
                    create_dir(Path(ROOT_PATH) / data['path'])
                    logger.info(f'Created directory {data["path"]}')
                    self.send_packet(PacketType.REQUEST, 'null')
                except Exception as e:
                    self.send_packet(PacketType.INVALID, f'Error creating directory {data["path"]}: {e}')
                    logger.error(f'Error creating directory {data["path"]}: {e}')

            case 'download':
                # maybe refactor this to be a function, had trouble with circular imports
                try:
                    # send client file info
                    logger.debug(f'Sending file info for {Path(ROOT_PATH) / data["path"] }')
                    file_size, file_name = get_file_info(Path(ROOT_PATH) / data['path'])
                    self.send_packet(PacketType.REQUEST, {
                        'type' : 'download',
                        'size' : file_size,
                        'filename' : file_name
                    })

                    logger.debug(f'Sending file {Path(ROOT_PATH) / data["path"]}')
                    with open(Path(ROOT_PATH) / data['path'], 'rb') as file:
                        while data := file.read(BUFFER_SIZE):
                            self.send_packet(PacketType.SEND, {
                                'data' : base64.b64encode(data).decode('utf-8')
                            })

                    # send null packet to signify end of file
                    self.send_packet(PacketType.SEND, {
                        'data' : 'null'
                    })

                    logger.debug(f'Finished sending file {Path(ROOT_PATH) / file_name}')
                except Exception as e:
                    self.send_packet(PacketType.INVALID, f'Error sending file {file_name}: {e}')
                    logger.error(f'Error sending file {file_name}: {e}')
            
            case _:
                logger.error(f'Invalid packet subtype received from {self.client_ip}, received subtype {data["type"]}')

    def handle_disconnect_packet(self, size, data):
        self.stop()
        self.close()
        self.server.disconnect_client(self)
    
    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.is_set()

    def close(self):
        self.client_socket.close()



if __name__ == '__main__':
    try:
        server = Server()
        server.run()
    except Exception as ex:
        logger.info(f'Server shutting down via {ex}')
    finally:
        server.close()
    