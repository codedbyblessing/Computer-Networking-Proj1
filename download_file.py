import socket
import os
import sys
from network_utils import send_json, receive_json_from, receive_bytes_from

TRACKER_ADDR = ('127.0.0.1', 6000)
OUTPUT_DIR = "client_downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Download a single chunk from a specified peer
def download_chunk(peer_ip, peer_port, file_name, chunk_index, size):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((peer_ip, peer_port))

        # Request chunk from peer
        metadata = {
            "type": "GET_CHUNK",
            "filename": file_name,
            "chunk_index": chunk_index,
            "size": size
        }
        send_json(s, metadata)

        # Wait for READY
        response = s.recv(1024).decode('utf-8')
        if response != "READY":
            raise Exception(f"Peer {peer_ip}:{peer_port} not ready")

        # Receive exact bytes for this chunk
        chunk_data = receive_bytes_from(s, size)
        if not chunk_data:
            raise Exception(f"Failed to download chunk {chunk_index}")

        # Confirm received
        s.sendall(b"STORED")

        return chunk_data


def download(file_name):
    # Get info from tracker
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(TRACKER_ADDR)
        request = {"type": "GET_FILE", "file_name": file_name}
        send_json(s, request)

        response = receive_json_from(s)
        if response["status"] != "OK":
            print(f"File '{file_name}' not found on tracker")
            return

        metadata = response["data"]
        total_chunks = metadata["total_chunks"]
        locations = metadata["locations"]

    print(f"File '{file_name}' has {total_chunks} chunks")

    # Download all chunks
    chunks = [None] * total_chunks
    for chunk_index in range(total_chunks):
        chunk_info = locations[str(chunk_index)]
        peer_ip = chunk_info["ip"]
        peer_port = chunk_info["port"]
        chunk_size = chunk_info["size"]

        print(f"Downloading chunk {chunk_index} from {peer_ip}:{peer_port} ({chunk_size} bytes)")
        chunk_data = download_chunk(peer_ip, peer_port, file_name, chunk_index, size=chunk_size)
        chunks[chunk_index] = chunk_data

    # Reconstruct file at output path
    output_path = os.path.join(OUTPUT_DIR, file_name)
    with open(output_path, 'wb') as f:
        for c in chunks:
            f.write(c)

    print(f"File downloaded successfully: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download.py (name of file)")
        sys.exit(1)

    filename = sys.argv[1]
    download(filename)