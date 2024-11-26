from net import *
import asyncio
import base64
import ntplib
import tkinter as tk

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
    packet_type, _, data = client.receive_packet()
    if packet_type == PacketType.INVALID:
        raise Exception(data)

    return data['data']

def get_filesize_string(file_size: int, index=0):
    # are we ever going to need more than GB? No. Are we going to add it anyways? Yes.
    file_size_units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    if file_size < 1024:
        return f'{file_size}{file_size_units[index]}'
    else:
        return get_filesize_string(int(file_size / 1024), index + 1)


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
            treeview.insert(parent, 'end', text=key, values=(get_filesize_string(value)))

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

    packet_type, data = wait_for_confirmation(client)

    if packet_type == PacketType.INVALID:
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

# could encapsulate this in a class
total_bytes_received = 0
total_file_size = 1

'''
Schedules a download status check on a separate thread
'''
def schedule_download_status_check(client, t: Thread, file_name, progress_bar, download_status, root: tk.Tk):
    root.after(100, check_download_status, client, t, file_name, progress_bar, download_status, root)
    

'''
Checks the download status of a file have to do it this way because 
tkinter is very finnicky about threading
'''
def check_download_status(client, t: Thread, file_name, progress_bar, download_status, root: tk.Tk):
    if not t.is_alive():
        download_status.set(f'Finished downloading {file_name}')
        progress_bar.set(200)
    else:
        progress_bar.set(total_bytes_received/total_file_size * 100 * 2)
        download_status.set(f'Downloading {file_name}... {round(total_bytes_received / total_file_size * 100, 2)}%')
        schedule_download_status_check(client, t, file_name, progress_bar, download_status, root)

def download_file_handler(client, path, save_path, progress_bar, download_status):
    logger.debug(f'Requesting to download file {path}')
    client.send_packet(PacketType.REQUEST, {
        'type' : 'download',
        'path' : path,
        "ntpStart": getNTPTime()
    })

    packet_type, data = wait_for_confirmation(client)

    if packet_type == PacketType.INVALID.value:
        raise Exception(data) # data will contain the error message

    with open(Path(save_path) / data['filename'], 'wb') as file:
        global total_bytes_received
        global total_file_size
        total_bytes_received = 0
        total_file_size = data['size']
        packet_data = {'data' : 'not null'}

        logger.debug(f'Starting to download file {data["filename"]}')
        while True:
            packet_type, packet_size, packet_data = client.receive_packet()
            
            # sevrer sends end of file packet
            if packet_data['data'] == 'null':
                break

            decoded_data = base64.b64decode(packet_data['data'].encode('utf-8'))
            total_bytes_received += len(decoded_data)
            file.write(decoded_data)
          
    logger.info(f'Finished downloading file {data["filename"]}')


def download_file(client, path, save_path, progress_bar, download_status, root: tk.Tk):
    file_name = Path(path).name

    progress_bar.set(0)
    download_status.set(f'Downloading... 0%')
    
    download_thread = threading.Thread(target=download_file_handler, args=(client, path, save_path, progress_bar, download_status))
    download_thread.start()

    check_download_status(client, download_thread, file_name, progress_bar, download_status, root)

    # update the ui while the thread is running
    while download_thread.is_alive():
        root.update()


