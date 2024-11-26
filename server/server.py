import socket
import struct
import threading
from sys import byteorder
from threading import Thread
from enum import Enum
import logging
from pathlib import Path
import datetime
import json

from cryptography.hazmat.primitives import serialization

import handleFolders
import handleFiles
import base64
import hashlib
import os
import ssl
from metrics import Metrics
import generateKeys
import cryptography.hazmat.primitives.asymmetric.rsa as rsa

# Load or define users and password hashes
user_db = {
    "user1": hashlib.sha256(b"password1").hexdigest(),
    "user2": hashlib.sha256(b"password2").hexdigest(),
}


class PacketType(Enum):
    LOGIN = 1
    SEND = 2
    REQUEST = 3
    DISCONNECT = 4
    INVALID = 5
    KEY = 6


# put in config file later
ROOT_PATH = "server_root"

LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    filename=Path(
        f'logs/log_{datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")}.log'
    ),
    level=LOG_LEVEL,
    format="[%(asctime)s][%(levelname)s]: %(message)s",
    filemode="w",
)
logger = logging.getLogger(__name__)
logger.info(f"Beginning log of {__name__}")

# to show log in console feel free to comment out
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(
    logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s")
)
logger.addHandler(console_handler)


BUFFER_SIZE = 4096
MAX_CLIENTS = 10
# read from config file later
HOST = "127.0.0.1"
PORT = 30000

# So multiple clients can download the same file at the same time
# or download a file currently being uploaded
lock = threading.Lock()


class Server:
    """
    Handles connections from multiple clients by establishing a new thread for each client
    each client handler is responsible for handling the client's requests and sending responses
    """

    def __init__(self):
        Thread.__init__(self)
        # only client handlers go in here
        self.connected_clients = []

        self.server_private_key, self.server_public_key, self.server_public_key_nums = generateKeys.generate_keys()

        # start server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(MAX_CLIENTS)
        # so server isn't waiting for connection forever (necessary to exit gracefully)
        self.server_socket.settimeout(0.5)

    """
    Listens for connections from clients and establishes a new thread for each client,
    runs on thread.start()
    """

    def run(self):
        logger.info(f"Server listening on {HOST}:{PORT}")

        # I know this looks bad but this was the only way I could get this to exit gracefully
        try:
            # listen for connection from client
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.info(f"Client from {addr} connected")
                    self.connect_new_client(client_socket, addr)
                except socket.timeout:
                    pass
                except Exception as e:
                    logger.error(f"Error connecting client {e}")

        except KeyboardInterrupt as e:
            logger.info(f"KeyboardInterrupt detected: Server exiting...")

    """
    Connects a new client to the server by establishing a new thread for the client
    """

    def connect_new_client(self, client_socket, ip_addr):
        client_handler = ClientHandler(client_socket, ip_addr, self)
        client_handler.start()  # check ClientHandler.run()

        self.connected_clients.append(client_handler)

    """
    Disconnects a client from the server
    """

    def disconnect_client(self, client_handler):
        self.connected_clients.remove(client_handler)
        logger.info(f"Client at {client_handler.client_ip} has disconnected")

    """
    Closes all connections to clients and stops all client threads
    """

    def close(self):
        for client in self.connected_clients:
            client.close()
            client.stop()

        self.server_socket.close()


class ClientHandler(Thread):
    """
    Handles requests from a single client, responsible for sending and receiving packets
    as well as controlling most of the server logic
    """

    def __init__(self, client_socket, client_ip, server):
        Thread.__init__(self)
        self.client_socket = client_socket
        self.client_ip = client_ip
        self.server = server

        self.client_public_key = None
        self.key, self.init_vector, self.aes_key = generateKeys.generate_symmetric_key()
        self.is_symmetric_sent = False

        # Magical flag to stop the thread as soon as it is set
        self._stop = threading.Event()

        self.client_socket.settimeout(1.0)

        self.clientMetrics = Metrics(client_ip, Path("metrics/clientMetrics.xlsx"))

        self.authenticated = False

    def encode_data(self, data):
        return json.dumps(data).encode("utf-8")

    def decode_data(self, data):
        return json.loads(data.decode("utf-8"))

    def create_packet(self, packet_type, data):
        # packet structure: [id, packet_type, data]
        data_bytes = self.encode_data(data)
        if  self.client_public_key is not None and self.is_symmetric_sent is False:
            data_bytes = generateKeys.encrypt_data(data_bytes, self.client_public_key)
        elif self.client_public_key is not None:
            data_bytes = generateKeys.symmetric_encrypt(data_bytes, self.aes_key)
        header = struct.pack("!BI", packet_type.value, len(data_bytes))

        return header + data_bytes

    def send_packet(self, packet_type, data):
        try:
            packet = self.create_packet(packet_type, data)
            #logger.debug(f'Packet: {packet}')
            self.client_socket.send(packet)
            logger.debug(f"Sent packet of type {packet_type} to {self.client_ip}")
        except Exception as e:
            logger.error(f"Unable to send packet: {e}")

    """
    Receives a packet from a client and returns a decoded dict
    """



    def receive_packet(self):
        # Read packet header
        packet_header = self.client_socket.recv(5)
        if len(packet_header) < 5:
            return None

        # make packet readable
        packet_type, packet_size = struct.unpack("!BI", packet_header)
        packet_bytes = self.client_socket.recv(packet_size)

        # in case the packet is split into multiple packets
        while len(packet_bytes) < packet_size:
            packet_bytes += self.client_socket.recv(packet_size - len(packet_bytes))

        #packet_data = self.decode_data(packet_bytes)
        #logger.debug(f'Packet Received: {packet_bytes}: ')
        # Decode the payload and load it as JSON
        if self.client_public_key is not None:
            packet_bytes = generateKeys.symmetric_decrypt(packet_bytes, self.aes_key)
        packet_data_str = packet_bytes.decode("utf-8")
        packet_data = json.loads(packet_data_str)  # Ensure packet_data is a dictionary

        return packet_type, packet_size, packet_data



    def wait_for_packet(self):
        # Unpack the packet directly and only proceed if we get a valid packet
        packet_type, packet_size, packet_data = self.receive_packet()
        if packet_type is not None and packet_data is not None:
            logger.debug(
                f"Received packet: type={packet_type}, size={packet_size}, data={packet_data}"
            )
            self.handle_packet(packet_type, packet_size, packet_data)
        else:
            logger.error(
                "Received an invalid or empty packet, skipping packet handling."
            )

    # runs all of the time on the thread
    def run(self):
        try:
            while True:
                # thread safe flag to stop the thread when the flag is set
                if self.stopped():
                    return

                try:
                    self.wait_for_packet()
                except socket.timeout:
                    pass

        except KeyboardInterrupt:
            pass
        finally:
            logger.debug(f"ClientHandler connected to {self.client_ip} stopping...")
            self.clientMetrics.processMetrics()
            self.close()

    def handle_packet(self, packet_type, packet_size, packet_data):
        if not self.authenticated and (packet_type != PacketType.LOGIN.value and packet_type != PacketType.DISCONNECT.value
            and packet_type != PacketType.KEY.value):
            logger.error(f'Client {self.client_ip} is not authenticated, skipping packet')
            self.send_packet(PacketType.INVALID, 'Client is not authenticated')
            return

        match packet_type:
            case PacketType.LOGIN.value:
                self.handle_login_packet(packet_data)
            case PacketType.SEND.value:
                self.handle_send_packet(packet_size, packet_data)
            case PacketType.REQUEST.value:
                self.handle_request_packet(packet_size, packet_data)
            case PacketType.DISCONNECT.value:
                self.handle_disconnect_packet(packet_size, packet_data)
            case PacketType.KEY.value:
                self.client_public_key = self.handle_key_packet(packet_data)
                keyval = self.key
                init_vec = self.init_vector
                keyval = base64.b64encode(keyval).decode("utf-8")
                init_vec = base64.b64encode(init_vec).decode("utf-8")
                aes_val = {'key': keyval, 'init_vector': init_vec}
                self.send_packet(PacketType.KEY, aes_val )
                logger.info(f'Sent symmetric key to client')
                self.is_symmetric_sent = True
            case _:
                self.handle_invalid_packet(packet_size, packet_data)

    def handle_invalid_packet(self, size, data):
        logger.error(f"Client from {self.client_ip} has sent an invalid packet.")

    def handle_login_packet(self, data):
        username = data.get("username")
        received_password_hash = data.get("password")
        stored_password_hash = user_db.get(username)

        if stored_password_hash and received_password_hash == stored_password_hash:
            self.authenticated = True
            self.send_packet(PacketType.LOGIN, {"status": "success"})
            logger.info(f"Client {self.client_ip} authenticated successfully.")
        else:
            self.send_packet(PacketType.INVALID, "Invalid credentials")
            logger.info(f"Client {self.client_ip} failed authentication.")

    def handle_key_packet(self, data):
        try:

            key_data = data  # self.decode_data(data)
            modulus = int.from_bytes(base64.b64decode(key_data['modulus']), byteorder='big')
            exp = int.from_bytes(base64.b64decode(key_data['exp']), byteorder='big')
            new_key_nums = rsa.RSAPublicNumbers(exp, modulus)
            cur_key = new_key_nums.public_key()
            logger.info(f'Received key from client')
            return cur_key

        except Exception as e:
            logger.error(f'Failed to receive key from client: {e}')

    def handle_send_packet(self, size, data):
        # put a match statement here so we can handle different types of sends (even though we never will)
        match data["type"]:
            case "upload":
                try:
                    logger.info(f'Received upload request for {data["path"]}')

                    total_bytes_received = 0
                    parent_dir = Path(ROOT_PATH) / Path(data["path"]).parent
                    if data["path"] == "":
                        data["path"] = data["filename"]
                    # if the parent directory is not a directory, we need to change the path
                    elif not parent_dir.is_dir():
                        data["path"] = parent_dir.parent / data["filename"]
                    elif parent_dir.is_dir():
                        data["path"] = parent_dir / data["filename"]

                    ntp_start = data[
                        "ntpStart"
                    ]  # initial upload packet will have ntpStart time

                    # receive file data
                    path = Path(data["path"])

                    if path.exists():
                        # !!!DO NOT CHANGE THE FSTRING OF EXCEPTION!!!
                        # Used for error identification on client side
                        raise Exception(f"FILENAME_EXISTS")
                    with open(path, "wb") as file:
                        # send confirmation packet if it is ok to upload
                        self.send_packet(PacketType.SEND, "null")

                        while True:
                            packet_type, packet_size, packet_data = (
                                self.receive_packet()
                            )

                            # client sends end of file packet
                            if packet_data["data"] == "null":
                                break

                            decoded_data = base64.b64decode(
                                packet_data["data"].encode("utf-8")
                            )
                            file.write(decoded_data)
                            total_bytes_received += len(decoded_data)

                    # send confirmation packet
                    self.send_packet(PacketType.SEND, "null")

                    # wrap metrics in try-catch to prevent server from sending invalid packet
                    try:
                        ntp_end = self.clientMetrics.getNTPTime()

                        self.clientMetrics.calculateMetrics(
                            operationType="upload",
                            ntpStart=ntp_start,
                            ntpEnd=ntp_end,
                            bytes_transferred=total_bytes_received,
                        )
                    except Exception as e:
                        logger.error(f"Error collecting metrics {e}")

                    logger.info(f'Finished uploading file {data["path"]}')
                except Exception as e:
                    logger.error(f'Error uploading file {data["filename"]}: {e}')
                    self.send_packet(PacketType.INVALID, str(e))

            case _:
                logger.error(
                    f'Invalid packet subtype received from {self.client_ip}, received subtype {data["type"]}'
                )

    def handle_request_packet(self, size, data):
        match data["type"]:
            case "filetree":
                try:
                    filetree = handleFolders.list_dir(Path(handleFiles.ROOT_PATH))
                    self.send_packet(
                        PacketType.SEND, {"type": "filetree", "data": filetree}
                    )
                except Exception as e:
                    logger.error(f"Error handling file tree: {e}")
                    self.send_packet(
                        PacketType.INVALID, f"SERVER: Error handling file tree: {e}"
                    )

            case "delete":
                logger.debug(
                    f'Deleting file {Path(handleFiles.ROOT_PATH) / data["path"]}'
                )
                try:
                    if (Path(handleFiles.ROOT_PATH) / data["path"]).is_dir():
                        handleFolders.delete_dir(Path(handleFiles.ROOT_PATH) / data["path"])
                    else:
                        handleFiles.delete_file(Path(handleFiles.ROOT_PATH) / data["path"])
                    logger.info(f'Deleted file {data["path"]}')
                    self.send_packet(PacketType.REQUEST, "null")
                except Exception as e:
                    logger.error(f'Error deleting file {data["path"]}: {e}')
                    self.send_packet(
                        PacketType.INVALID, f'Error deleting file {data["path"]}: {e}'
                    )

            case "create_dir":
                try:
                    handleFolders.create_dir(Path(handleFiles.ROOT_PATH) / data["path"])
                    logger.info(f'Created directory {data["path"]}')
                    self.send_packet(PacketType.REQUEST, "null")
                except Exception as e:
                    self.send_packet(
                        PacketType.INVALID,
                        f'Error creating directory {data["path"]}: {e}',
                    )
                    logger.error(f'Error creating directory {data["path"]}: {e}')

            case "download":
                # maybe refactor this to be a function, had trouble with circular imports
                try:
                    # send client file info
                    path = Path(ROOT_PATH) / data["path"]
                    logger.debug(f"Sending file info for {path}")
                    file_size, file_name = handleFiles.get_file_info(path)
                    if not path.exists():
                        raise FileNotFoundError(f'File {data["path"]} does not exist')
                    self.send_packet(
                        PacketType.REQUEST,
                        {"type": "download", "size": file_size, "filename": file_name},
                    )

                    ntp_start = data[
                        "ntpStart"
                    ]  # initial download packet will have ntpStart time

                    logger.debug(f"Sending file {path}")
                    with open(path, "rb") as file:
                        while data := file.read(BUFFER_SIZE):
                            self.send_packet(
                                PacketType.SEND,
                                {"data": base64.b64encode(data).decode("utf-8")},
                            )

                    # send null packet to signify end of file
                    self.send_packet(PacketType.SEND, {"data": "null"})

                    logger.debug(f"Finished sending file {Path(ROOT_PATH) / file_name}")

                    try:
                        ntp_end = self.clientMetrics.getNTPTime()

                        self.clientMetrics.calculateMetrics(
                            operationType="download",
                            ntpStart=ntp_start,
                            ntpEnd=ntp_end,
                            bytes_transferred=file_size,
                        )
                    except Exception as e:
                        logger.error(f"Error collecting metrics {e}")

                except Exception as e:
                    logger.error(e)
                    self.send_packet(PacketType.INVALID, str(e))

            case _:
                logger.error(
                    f'Invalid packet subtype received from {self.client_ip}, received subtype {data["type"]}'
                )
                self.send_packet(
                    PacketType.INVALID,
                    f'Invalid packet subtype received: {data["type"]}',
                )

    """
    Handles the disconnect packet from the client and closes the connection
    """

    def handle_disconnect_packet(self, size, data):
        self.stop()
        self.close()
        self.server.disconnect_client(self)

    """
    Sets the stop flag to true, stopping the thread
    """

    def stop(self):
        self._stop.set()

    """
    Returns true if the stop flag is set
    """

    def stopped(self):
        return self._stop.is_set()

    """
    Closes the client socket
    """

    def close(self):
        self.client_socket.close()


if __name__ == "__main__":
    try:
        server = Server()
        server.run()
    except Exception as ex:
        logger.info(f"Server shutting down via {ex}")
    finally:
        server.close()
