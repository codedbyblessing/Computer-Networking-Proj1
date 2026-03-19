import socket
import os
import sys
from network_utils import send_json, receive_json_from, receive_bytes_from

if len(sys.argv) != 2:
    print("Usage: python peer.py (peer #)")
    sys.exit(1)

# increment port num by peer #
PORT = 5001 + int(sys.argv[1])
HOST = '0.0.0.0'
STORAGE_DIRECTORY = "peer_storage"

os.makedirs(STORAGE_DIRECTORY, exist_ok=True)

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
            size = metadata.get("size", None)

            print(f"{addr} Receiving chunk {chunk_index} of {size} bytes")
            # Signal that the peer is ready to download the chunk
            conn.sendall(b"READY")

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

def register_with_tracker():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 6000))

            data = {
                "type": "REGISTER_PEER",
                "ip": "127.0.0.1",
                "port": PORT
            }

            send_json(s, data)
            print(f"Registered peer with tracker: {PORT}")

    except Exception as e:
        print(f"Failed to register peer with tracker: {e}")

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
    register_with_tracker()
    init_peer()