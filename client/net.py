import socket
import struct
import threading
from threading import Thread
from enum import Enum
import logging
from pathlib import Path
import datetime

class PacketType(Enum):
    INVALID = -1
    LOGIN = 1
    SEND = 2
    REQUEST = 3
    DISCONNECT = 4


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


'''
The logging and error handling for client is done in this file, 
but in the future it would be smarter to handle it in main so we 
can relay errors to the ui easier 
'''

BUFFER_SIZE = 4096

class Client(Thread):
    def __init__(self, server_ip, server_port):
        Thread.__init__(self)
        self.server_ip = server_ip
        self.server_port = server_port

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # required to exit gracefully
        self.client_socket.settimeout(0.1)

        # Flag used for thread safety
        self._stop = threading.Event()

    def connect(self):
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            logger.info(f'Connected to server at {self.server_ip}:{self.server_port}')

            # send login information later if doing extra credit
            self.send_packet(PacketType.LOGIN, 'hihihihi')
        except Exception as e:
            logger.error(f'Failed to connect to server: {e}')

    def disconnect(self):
        # no data required for disconnect
        self.send_packet(PacketType.DISCONNECT, 'null')

        self.stop()
        self.close()
     
        
    def create_packet(self, packet_type, data):
        # packet structure: [id, packet_type, data]
        data_bytes = data.encode('utf-8')
        header = struct.pack('!BI', packet_type.value, len(data_bytes))

        return header + data_bytes
    
    def send_packet(self, packet_type, data):
        packet = self.create_packet(packet_type, data)
        self.client_socket.send(packet)

    def receive_packet(self):
        # Read packet header
        packet_header = self.client_socket.recv(5)
        if len(packet_header) < 5:
            return None
        
        # make packet readable
        packet_type, packet_size = struct.unpack('!BI', packet_header)
        packet_data = self.client_socket.recv(packet_size).decode()

        logger.info(f'packet received of type {packet_type}')

        self.handle_packet(packet_type, packet_size, packet_data)

    # runs all of the time on the thread
    def run(self):
        try:
            while not self.stopped():
                try:
                    self.receive_packet()
                except socket.timeout:
                    pass

        # client errors on close if this isn't here
        # if another fix is found feel free to change 
        except Exception:
            pass
        finally: 
            logger.info(f'Client shutting down...')

    def handle_packet(self, type, size, data):
        match type:
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


        