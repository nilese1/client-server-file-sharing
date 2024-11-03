from net import *
import asyncio

'''
This file will be used to send packets of the request 
type: getting the filetree, downloading files etc.
'''


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
