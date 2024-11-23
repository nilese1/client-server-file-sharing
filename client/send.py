from net import *
import base64
import ntplib
from tkinter import simpledialog
import tkinter as tk
import pathlib


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


# Sends a file to the client when the client requests a download
def get_file_info(path: Path):
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f'File {path} does not exist or is not a file')

    file_size = path.stat().st_size
    file_name = path.name

    return file_size, file_name

# global variables could encapsulate this in a class
total_bytes_sent = 0
total_file_size = 1

'''
Schedules a download status check on a separate thread
'''
def schedule_upload_status_check(client, t: Thread, file_name, progress_bar, upload_status, root: tk.Tk):
    root.after(100, check_upload_status, client, t, file_name, progress_bar, upload_status, root)
    

'''
Checks the download status of a file have to do it this way because 
tkinter is very finnicky about threading
'''
def check_upload_status(client, t: Thread, file_name, progress_bar, upload_status, root: tk.Tk):
    if not t.is_alive():
        upload_status.set(f'Finished uploading {file_name}')
        progress_bar.set(200)
    else:
        progress_bar.set(total_bytes_sent/total_file_size * 100 * 2)
        upload_status.set(f'Uploading {file_name}... {round(total_bytes_sent / total_file_size * 100, 2)}%')

        # if we've sent the entire file, wait for server to finish processing
        if total_bytes_sent >= total_file_size:
            upload_status.set(f'Waiting for server to finish processing...')

        schedule_upload_status_check(client, t, file_name, progress_bar, upload_status, root)


def upload_file_handler(client, file_to_upload, destination_path, progress_bar, upload_status):
    global total_bytes_sent
    global total_file_size

    logger.info(f'Uploading file {file_to_upload} to {destination_path}')

    file_size, file_name = get_file_info(Path(file_to_upload))

    total_file_size = file_size

    client.send_packet(PacketType.SEND, {
        'type' : 'upload',
        'size' : file_size,
        'filename' : file_name,
        'path' : destination_path,
        'ntpStart': getNTPTime()
    })

    # server will send a confirmation packet to accept upload
    packet_type, _, data = client.receive_packet()

    if packet_type == PacketType.INVALID.value and data != "FILENAME_EXISTS":
        raise Exception(data)
    elif packet_type == PacketType.INVALID.value and data == "FILENAME_EXISTS":
        new_name = rename_file(file_name)
        upload_file_handler(client, file_to_upload, str(Path(destination_path).with_name(new_name)), progress_bar, upload_status)
        return
    
    total_bytes_sent = 0

    # begin sending file (plenty of consent)
    with open(file_to_upload, 'rb') as file:
        while data := file.read(BUFFER_SIZE):
            client.send_packet(PacketType.SEND, {
                'data' : base64.b64encode(data).decode('utf-8')
            })

            total_bytes_sent += len(data)

    # send null packet to signify end of file
    client.send_packet(PacketType.SEND, {
        'data' : 'null'
    })

    # wait for server to finish processing
    packet_type, _, data = client.receive_packet()

    if packet_type == PacketType.INVALID:
        raise Exception(data)

    logger.info(f'Finished uploading file {file_to_upload} to {destination_path}')


def upload_file(client, file_to_upload, destination_path, progress_bar, upload_status, root: tk.Tk):
    file_name = Path(file_to_upload).name

    upload_thread = Thread(target=upload_file_handler, args=(client, file_to_upload, destination_path, progress_bar, upload_status))
    upload_thread.start()
    schedule_upload_status_check(client, upload_thread, file_name, progress_bar, upload_status, root)


def rename_file(old_filename):
    input_box = simpledialog.askstring("File Already Exists", "Please enter a different file name")


    return input_box + Path(old_filename).suffix
    