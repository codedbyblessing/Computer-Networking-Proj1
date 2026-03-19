import socket
import json
import os
import struct
import sys

CHUNK_SIZE = 1024 * 1024
PEERS = [('127.0.0.1', 5001), ('127.0.0.1', 5002)]
TRACKER_ADDR = ('127.0.0.1', 6000)
BUFFER_SIZE = 1024  # for small messages like READY/STORED


# Sends JSON + length to the specified socket
def send_json(sock: socket.socket, data: dict):
    encoded = json.dumps(data).encode('utf-8')
    sock.sendall(struct.pack('!I', len(encoded)))
    sock.sendall(encoded)


# Receives status updates from peers
def recv_msg(sock: socket.socket) -> str:
    return sock.recv(BUFFER_SIZE).decode('utf-8')


# Create 1 MB chunks from the specified file
def chunk_file(file_path: str):
    with open(file_path, 'rb') as f:
        chunk_index = 0
        while True:
            chunk_data = f.read(CHUNK_SIZE)
            if not chunk_data:
                break
            yield chunk_index, chunk_data
            chunk_index += 1


# Send 1 file chunk to the specified peer. Return the peer IP/port # and chunk size to later store in the tracker
def send_chunk_to_peer(chunk_index: int, chunk_data: bytes, peer: tuple, file_name: str):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(peer)

            # 1. Send metadata
            metadata = {
                "type": "NEW_CHUNK",
                "filename": file_name,
                "chunk_index": chunk_index,
                "size": len(chunk_data)
            }
            send_json(s, metadata)

            # 2. Wait for READY
            if recv_msg(s) != "PEER_READY":
                raise Exception("Peer isn't ready")

            # 3. Send chunk data
            s.sendall(chunk_data)

            # 4. Wait for STORED
            if recv_msg(s) != "CHUNK_STORED":
                raise Exception("Chunk wasn't stored")

            print(f"Stored chunk {chunk_index} with {peer}")
            return {"ip": peer[0], "port": peer[1], "size": len(chunk_data)}

    except Exception as e:
        print(f"Upload client: couldn't send {chunk_index} to {peer}: {e}")
        raise


# Register the filename, size, and locations of each chunk with the tracker
def register_with_tracker(file_name: str, total_chunks: int, chunk_locations: dict):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(TRACKER_ADDR)
            data = {
                "type": "NEW_FILE",
                "file_name": file_name,
                "total_chunks": total_chunks,
                "locations": chunk_locations
            }
            send_json(s, data)
            print(f"Upload client: Successfully registered {file_name}.")
    except Exception as e:
        print(f"Upload client: couldn't register with the tracker.{e}")

# Register a new uploaded file. Chunking, sending to peers, and registering chunk info
# with the tracker.
def upload_file(file_path: str):
    file_name = os.path.basename(file_path)
    chunk_locations = {}

    print(f"Upload client: chunking {file_name}")
    success = True

    for chunk_index, chunk_data in chunk_file(file_path):
        target_peer = PEERS[chunk_index % len(PEERS)]
        try:
            info = send_chunk_to_peer(chunk_index, chunk_data, target_peer, file_name)
            chunk_locations[chunk_index] = info
        except Exception:
            success = False
            break

    if success:
        register_with_tracker(file_name, len(chunk_locations), chunk_locations)
        print("Upload client: registered chunks with tracker")
    else:
        print("Upload client: an error occured in distributing the file chunks.")


# ------------------------
# Command-line Interface
# ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 alice.py <file_path_to_share>")
        sys.exit(1)

    file_path = sys.argv[1]
    upload_file(file_path)