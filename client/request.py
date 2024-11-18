from net import *
import asyncio
import base64
import ntplib

'''
This file will be used to send packets of the request 
type: getting the filetree, downloading files etc.
'''

'''
For performance metrics. Send ntptime with download and upload requests
'''
def getNTPTime():
    ntpClient = ntplib.NTPClient()
    try:
        ntp_res = ntpClient.request("0.pool.ntp.org", version=3)
        return ntp_res.tx_time
    except Exception as e:
        print(f"Error getting NTP time, returning -1")
        return -1


'''
returns a dict that accurately represents the file structure that's present on the server
'''
def get_filetree(client):
    client.send_packet(PacketType.REQUEST, {
        'type' : 'filetree',
        'data' : 'null'
    })

    data = {'data' : 'null'}
    _, _, data = client.receive_packet()

    return data['data']
    

'''
Displays the file structure in a treeview given a dict (and parent if filetree is a subtree)
'''
def load_filetree(treeview, filetree: dict, parent=None):
    parent = parent if parent else ''

    for key, value in filetree.items():
        if isinstance(value, dict):
            item = treeview.insert(parent, 'end', text=key)
            load_filetree(treeview, value, item)
        else:
            treeview.insert(parent, 'end', text=key)

'''
Waits for a confirmation packet from the server, going to be our main way of
handling errors on the server side and relaying information to the user
'''
def wait_for_confirmation(client):
    type, size, data = client.receive_packet()

    return type, data


def delete_file_handler(client, path):
    client.send_packet(PacketType.REQUEST, {
        'type' : 'delete',
        'path' : path
    })

    type, data = wait_for_confirmation(client)

    if type == PacketType.INVALID:
        raise Exception(data) # data will contain the error message

    return data

def create_directory_handler(client, path):
    client.send_packet(PacketType.REQUEST, {
        'type' : 'create_dir',
        'path' : path
    })

    type, data = wait_for_confirmation(client)

    if type == PacketType.INVALID:
        raise Exception(data) # data will contain the error message

    return data


def download_file_handler(client, path, progress_bar, save_path):
    logger.debug(f'Requesting to download file {path}')
    client.send_packet(PacketType.REQUEST, {
        'type' : 'download',
        'path' : path,
        "ntpStart": getNTPTime()
    })

    type, data = wait_for_confirmation(client)

    if type == PacketType.INVALID:
        raise Exception(data) # data will contain the error message

    with open(Path(save_path) / data['filename'], 'wb') as file:
        total_bytes_received = 0
        total_file_size = data['size']
        progress_bar.set(0)
        packet_data = {'data' : 'not null'}

        logger.debug(f'Starting to download file {data["filename"]}')
        # server sends null packet to signify end of file
        while packet_data['data'] != 'null':
            packet_type, packet_size, packet_data = client.receive_packet() 
            decoded_data = base64.b64decode(packet_data['data'].encode('utf-8'))
            total_bytes_received += len(decoded_data)
            file.write(decoded_data)
            # not sure why we need to multiply by 2 here, but it works
            # also, put on separate thread later so it actually updates in real time
            progress_bar.set(total_bytes_received/total_file_size * 100 * 2)
        
    logger.debug(f'Finished downloading file {data["filename"]}')


