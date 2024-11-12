from net import *
import base64

# Sends a file to the client when the client requests a download
def get_file_info(path: Path):
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f'File {path} does not exist or is not a file')

    file_size = path.stat().st_size
    file_name = path.name

    return file_size, file_name

 

def upload_file_handler(client, file_to_upload, destination_path):
    logger.info(f'Uploading file {file_to_upload} to {destination_path}')

    file_size, file_name = get_file_info(Path(file_to_upload))

    client.send_packet(PacketType.SEND, {
        'type' : 'upload',
        'size' : file_size,
        'filename' : file_name,
        'path' : destination_path
    })

    # server will send a confirmation packet to accept upload
    type, _, data = client.receive_packet()

    if type == PacketType.INVALID:
        raise Exception(data)

    # begin sending file (plenty of consent)
    with open(file_to_upload, 'rb') as file:
        while data := file.read(BUFFER_SIZE):
            client.send_packet(PacketType.SEND, {
                'data' : base64.b64encode(data).decode('utf-8')
            })

    # send null packet to signify end of file
    client.send_packet(PacketType.SEND, {
        'data' : 'null'
    })

    # wait for server to finish processing
    type, _, data = client.receive_packet()

    if type == PacketType.INVALID:
        raise Exception(data)

    logger.info(f'Finished uploading file {file_to_upload} to {destination_path}')

    