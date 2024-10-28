import socket
import struct
from threading import Thread
from enum import Enum

class PacketType(Enum):
    INVALID = -1
    LOGIN = 1
    SEND = 2
    REQUEST = 3
    DISCONNECT = 4


BUFFER_SIZE = 4096
MAX_CLIENTS = 10
# read from config file later
HOST = '127.0.0.1'
PORT = 30000



class Server:
    def __init__(self):
        # only client handlers go in here
        self.connected_clients = []

        # start server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(MAX_CLIENTS) 

    def run(self):
        print(f'Server listening on {HOST}:{PORT}')

        # listen for connection from client
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f'Client from {addr} connected')
            self.connect_new_client(client_socket)

    def connect_new_client(self, client_socket):
        client_handler = ClientHandler(client_socket)
        client_handler.start() # check ClientHandler.run()

        self.connected_clients.append(client_handler)

    def close(self):
        for client in self.connected_clients:
            client.close()

        self.server_socket.close()

class ClientHandler(Thread):
    def __init__(self, client_socket):
        Thread.__init__(self)
        self.client_socket = client_socket

    def receive_packet(self):
        # Read packet header
        packet_header = self.client_socket.recv(5)
        if len(packet_header) < 5:
            return None
        
        # make packet readable
        packet_type, packet_size = struct.unpack('!BI', packet_header)
        packet_data = self.client_socket.recv(packet_size).decode()

        print(f'packet received of type {packet_type}')

        self.handle_packet(packet_type, packet_size, packet_data)

    # runs all of the time on the thread
    def run(self):
        while True:
           self.receive_packet() 

    def handle_packet(self, type, size, data):
        match type:
            case PacketType.LOGIN:
                self.handle_login_packet(type, size, data)
            
            case PacketType.SEND:
                self.handle_login_packet(type, size, data)

            case PacketType.REQUEST: 
                self.handle_request_packet(type, size, data)

            case PacketType.DISCONNECT:
                self.handle_disconnect_packet(type, size, data)

            case _:
                self.handle_invalid_packet(type, size, data)

    # TODO: implement packet handlers
    def handle_invalid_packet(self, type, size, data):
        pass

    def handle_login_packet(self, type, size, data):
        pass

    def handle_send_packet(self, type, size, data):
        pass
    
    def handle_request_packet(self, type, size, data):
        pass

    def handle_disconnect_packet(self, type, size, data):
        pass

    def close(self):
        self.client_socket.close()



if __name__ == '__main__':
    server = Server()

    try:
        server.run()
    except KeyboardInterrupt:
        print("Bye Bye")
    finally:
        server.close()
