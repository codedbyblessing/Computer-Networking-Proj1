import socket
import os
import sys
from network_utils import send_json, receive_msg, recv_json

CHUNK_SIZE = 1024 * 1024
TRACKER_ADDR = ('127.0.0.1', 6000)


# Get peers dynamically from tracker
def get_peers_from_tracker():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(TRACKER_ADDR)
        send_json(s, {"type": "GET_PEERS"})
        response = recv_json(s)
        return response.get("peers", [])


# Create chunks
def chunk_file(file_path: str):
    with open(file_path, 'rb') as f:
        chunk_index = 0
        while True:
            chunk_data = f.read(CHUNK_SIZE)
            if not chunk_data:
                break
            yield chunk_index, chunk_data
            chunk_index += 1

# Send chunk to peer
def send_chunk_to_peer(chunk_index, chunk_data, peer, file_name):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(tuple(peer)) #keeping the data structure consistent

            metadata = {
                "type": "NEW_CHUNK",
                "filename": file_name,
                "chunk_index": chunk_index,
                "size": len(chunk_data)
            }
            send_json(s, metadata)

            if receive_msg(s) != "READY":
                raise Exception("Peer isn't ready")

            s.sendall(chunk_data)

            if receive_msg(s) != "CHUNK_STORED":
                raise Exception("Chunk wasn't stored")

            print(f"Stored chunk {chunk_index} with {peer}")
            return {"ip": peer[0], "port": peer[1], "size": len(chunk_data)}

    except:
        print(f"Upload client: couldn't send {chunk_index} to {peer}: {e}")
        raise
# Register file with tracker
def register_with_tracker(file_name, total_chunks, chunk_locations):
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
    except:
        print(f"Upload client: couldn't register with the tracker: {e}")

#CHUNK upload logic
def upload_file(file_path):
    file_name = os.path.basename(file_path)
    chunk_locations = {}
    peers = get_peers_from_tracker()
    if len(peers) < 2:
        print("Not enough peers available.")
        return

    print(f"Upload client: chunking {file_name}")
    success = True

    for chunk_index, chunk_data in chunk_file(file_path):
        target_peer = peers[chunk_index % len(peers)]
        try:
            info = send_chunk_to_peer(chunk_index, chunk_data, target_peer, file_name)
            chunk_locations[str(chunk_index)] = info   # ✅ FIX: string key
        except Exception:
            success = False
            break
    if success:
        register_with_tracker(file_name, len(chunk_locations), chunk_locations)
        print("Upload client: registered chunks with tracker")
    else:
        print("Upload client: error distributing file chunks.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 share_file.py path/to/file")
        sys.exit(1)

    file_path = sys.argv[1]
    upload_file(file_path)