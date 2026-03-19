import socket
import json
import struct
import os
import sys

if len(sys.argv) != 2:
    print("Usage: python peer.py (peer #)")
    sys.exit(1)

# increment port num by peer #
PORT = 5001 + int(sys.argv[1])
HOST = '0.0.0.0'
STORAGE_DIRECTORY = "peer_storage"

os.makedirs(STORAGE_DIRECTORY, exist_ok=True)

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
    return json.loads(data.decode('utf-8'))

# Handle client messages
def handle_client(conn, addr):
    try:
        # Receive message from the client
        metadata = receive_json_from(conn)
        if not metadata:
            return

        msg_type = metadata.get("type")
        # handle different message types

        # Peer is receiving a chunk
        if msg_type == "NEW_CHUNK":
            # Get chunk information
            filename = metadata["filename"]
            chunk_index = metadata["chunk_index"]
            size = metadata["size"]

            print(f"{addr} Receiving chunk {chunk_index} of {size} bytes")
            # Signal that the peer is ready to download the chunk
            conn.sendall(b"PEER_READY")

            # Attempt to receive chunk
            chunk_data = receive_bytes_from(conn, size)
            if not chunk_data:
                print(F"{addr} Failed to receive the chunk")
                return

            # Write chunk to the output directory
            chunk_filename = f"{filename}_{chunk_index}"
            path = os.path.join(STORAGE_DIRECTORY, chunk_filename)
            with open(path, 'wb') as file:
                file.write(chunk_data)

            print(f"Stored chunk {chunk_filename}")

            conn.sendall(b"CHUNK_STORED")

        # Peer needs to deliver a chunk
        elif msg_type == "GET_CHUNK":
            # Get chunk information
            filename = metadata["filename"]
            chunk_index = metadata["chunk_index"]
            size = metadata["size"]
            
            # Check if chunk exists in the storage directory
            chunk_filename = f"{filename}_{chunk_index}"
            path = os.path.join(STORAGE_DIRECTORY, chunk_filename)
            if not os.path.exists(path):
                print(f"Chunk {chunk_filename} does not exist")
                return

            # Signal that the peer is ready to deliver the chunk
            conn.sendall(b"READY")
            # Send the chunk
            with open(path, 'rb') as f:
                data = f.read()
                conn.sendall(data)

            # Check for acknowledgement
            ack = conn.recv(1024)
            if ack != b"STORED":
                print(f"Chunk {chunk_index} not acknowledged")

            print(f"Chunk {chunk_index} sent to {addr}")

        else:
            print(f"Invalid message {addr}: {msg_type}")

    except Exception as e:
        print(f"Error {addr}: {e}")

    finally:
        conn.close()


def init_peer():
    # Initialize socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()

        print(f"New peer on port {PORT}")
        # Listen for messages
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    init_peer()