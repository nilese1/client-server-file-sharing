import socket
import struct
import threading
from threading import Thread
from enum import Enum
import logging
from pathlib import Path
import datetime
import json
import base64
import hashlib
from types import NoneType

from cryptography.hazmat.primitives import serialization

import encryption
import cryptography.hazmat.primitives.asymmetric.rsa as rsa

class PacketType(Enum):
    LOGIN = 1
    SEND = 2
    REQUEST = 3
    DISCONNECT = 4
    INVALID = 5 # used for errors, changed from -1 to 5 because apparently struct only accepts unsigned ints
    KEY = 6


LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.info(f'Beginning log of {__name__}')
logging.basicConfig(filename=Path(f'logs/log_{datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")}.log'), level=LOG_LEVEL,
                    format='[%(asctime)s][%(levelname)s]: %(message)s', filemode='w')

# to show log in console feel free to comment out
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s'))
logger.addHandler(console_handler)

BUFFER_SIZE = 4096


'''
The logging and error handling for client is done in this file, 
but in the future it would be smarter to handle it in main so we 
can relay errors to the ui easier 
'''
class Client(Thread):
    def __init__(self, server_ip, server_port):
        Thread.__init__(self)
        self.server_ip = server_ip
        self.server_port = server_port

        self.private_key_client, self.public_key_client, self.public_key_client_numbers  = encryption.generate_keys()
        self.AES_KEY = None

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # required to exit gracefully
        self.client_socket.settimeout(2.0)

        # Flag used for thread safety
        self._stop = threading.Event()

    def connect(self):

        self.client_socket.connect((self.server_ip, self.server_port))
        logger.info(f'Connected to server at {self.server_ip}:{self.server_port}')

    def send_key(self):
        try:
            exp = self.public_key_client_numbers.e
            modulus = self.public_key_client_numbers.n

            modulus = base64.b64encode(modulus.to_bytes((modulus.bit_length() + 7) // 8, byteorder='big')).decode("utf-8")
            exp = base64.b64encode(exp.to_bytes((exp.bit_length() + 7) // 8, byteorder='big')).decode("utf-8")

            data = {"modulus": modulus, "exp": exp}
            self.send_packet(PacketType.KEY, data)
            logger.info(f'Sent public key to server')
        except Exception as e:
            logger.error(f'Failed to send public key to server: {e}')

    def get_key(self):
        try:
            packet_type, packet_size, packet_data = self.receive_packet()
            key = base64.b64decode(packet_data['key'].encode('utf-8'))
            init_vector = base64.b64decode(packet_data['init_vector'].encode('utf-8'))
            self.AES_KEY = encryption.generate_symmetric_key(key, init_vector)
            logger.info(f'Received key from server')

        except Exception as e:
            logger.error(f'Failed to receive key from server: {e}')


    # TODO: implement authentication
    def authenticate(self, username, password):
        # plaintext password is bad, but we'll fix it later
        self.send_packet(PacketType.LOGIN, {
            'username' : username,
            'password' : hashlib.sha256(password.encode('utf-8')).hexdigest()
        })

        # wait for server to confirm
        packet_type, _, data = self.receive_packet()
        if packet_type == PacketType.INVALID.value:
            raise Exception(data)
        
        # if no error, we can continue

    def disconnect(self):
        # no data required for disconnect
        self.send_packet(PacketType.DISCONNECT, 'null')

        self.stop()
        self.close()


    def encode_data(self, data):
        return json.dumps(data).encode('utf-8')
    
    def decode_data(self, data):
        return json.loads(data.decode('utf-8'))
        
    def create_packet(self, packet_type, data):
        # packet structure: [id, packet_type, data]
        data_bytes = self.encode_data(data)
        if self.AES_KEY is not None:
            data_bytes = encryption.symmetric_encrypt(data_bytes, self.AES_KEY)
        header = struct.pack('!BI', packet_type.value, len(data_bytes))

        return header + data_bytes
    
    def send_packet(self, packet_type, data):
        #data = encryption.encrypt_data(data, self.public_key_server)
        packet = self.create_packet(packet_type, data)
        #logger.debug(f'Packet: {packet}')
        self.client_socket.send(packet)


    def receive_packet(self):
        # Read packet header
        packet_header = self.client_socket.recv(5)
        if len(packet_header) < 5:
            return None

        logger.debug(f'packet header {packet_header}')

        # make packet readable
        packet_type, packet_size = struct.unpack('!BI', packet_header)

        packet_bytes = self.client_socket.recv(packet_size)

        # in case the packet is split into multiple packets
        while len(packet_bytes) < packet_size:
            packet_bytes += self.client_socket.recv(packet_size - len(packet_bytes))
        #logger.debug(f'Packet Rec: {packet_bytes}')
        if self.AES_KEY is not None:
            packet_bytes = encryption.symmetric_decrypt(packet_bytes, self.AES_KEY)
        elif self.AES_KEY is None and packet_type == PacketType.KEY.value:
            packet_bytes = encryption.decrypt_data(packet_bytes, self.private_key_client)


        packet_data = self.decode_data(packet_bytes)

        logger.info(f'packet received of type {PacketType(packet_type).name} and size {packet_size}')
        logger.debug(f'Packet info: {packet_data}')

        return packet_type, packet_size, packet_data


    def wait_for_packet(self):
        packet_type, packet_size, packet_data = self.receive_packet()
        self.handle_packet(packet_type, packet_size, packet_data)

    # runs all of the time on the thread
    def run(self):
        pass
        '''
        Commented this out because client is really only going to listen for disconnect packet
        and it causing weird issues with get_filetree function because I didn't want it in 
        the handle_packet function. Maybe if we fix this somehow we can add this back
        '''
        # try:
        #     while not self.stopped():
        #         try:
        #             self.wait_for_packet()
        #         except socket.timeout:
        #             pass

        # # client errors on close if this isn't here
        # # if another fix is found feel free to change 
        # except Exception:
        #     pass
        # finally: 
        #     logger.info(f'Client shutting down...')

    def handle_packet(self, type, size, data):
        match PacketType(type):
            case PacketType.SEND:
                self.handle_send_packet(type, size, data)

            case PacketType.REQUEST: 
                self.handle_request_packet(type, size, data)

            case _:
                self.handle_invalid_packet(type, size, data)

    # TODO: implement packet handlers
    def handle_invalid_packet(self, type, size, data):
        pass

    def handle_send_packet(self, type, size, data):
       pass 
    
    def handle_request_packet(self, type, size, data):
        pass
    
    def stop(self):
        logger.info(f'Client has been stopped')
        self._stop.set()

    def stopped(self):
        self._stop.is_set()

    def close(self):
        self.client_socket.close()



