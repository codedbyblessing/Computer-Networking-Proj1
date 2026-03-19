import json
import struct

# Receive exact num bytes
def receive_bytes_from(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

# Receive JSON with length info
def receive_json_from(sock):
    raw_length = receive_bytes_from(sock, 4)
    if not raw_length:
        return None
    # unpack message and return the decoded dict
    message_length = struct.unpack('!I', raw_length)[0]
    data = receive_bytes_from(sock, message_length)
    if not data: #logic, if the data does not exists, a clean way to safely return
        return None
    try:
        return json.loads(data.decode('utf-8'))
    except Exception:
        return None

def send_json(sock, data):
    encoded = json.dumps(data).encode('utf-8')
    sock.sendall(struct.pack('!I', len(encoded)))
    sock.sendall(encoded)

def receive_msg(sock):
    return sock.recv(1024).decode('utf-8')
