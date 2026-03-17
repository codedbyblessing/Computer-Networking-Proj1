import socket
import sys
import json
import os

def start_peer(port):
    peer_dir = f"peer_data_{port}"
    os.makedirs(peer_dir, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', port))
        s.listen()
        print(f"Peer listening on port {port}...")
        print(f"Data folder: ./{peer_dir}/")
        
        while True:
            conn, addr = s.accept()
            with conn:
                header_data = conn.recv(1024).decode('utf-8')
                if not header_data:
                    continue
                
                try:
                    header = json.loads(header_data)
                    req_type = header.get("type")
                    
                    if req_type == "new_chunk":
                        # ALICE IS UPLOADING TO THIS PEER
                        file_name = header.get("filename")
                        chunk_id = header.get("chunk_id")
                        filepath = os.path.join(peer_dir, f"{file_name}.part{chunk_id}")
                        
                        print(f"\n[Peer {port}] Alice is sending chunk {chunk_id} for {file_name}")
                        conn.sendall("READY".encode('utf-8')) # Send ACK
                        
                        # Save the incoming binary data
                        with open(filepath, 'wb') as f:
                            while True:
                                packet = conn.recv(4096)
                                if not packet: break
                                f.write(packet)
                        print(f"[Peer {port}] Successfully saved {filepath}")
                        
                    elif req_type == "request_chunk":
                        # BOB IS DOWNLOADING FROM THIS PEER
                        file_name = header.get("file_name")
                        chunk_id = header.get("chunk_id")
                        filepath = os.path.join(peer_dir, f"{file_name}.part{chunk_id}")
                        
                        print(f"\n[Peer {port}] Bob requested chunk {chunk_id} for {file_name}")
                        
                        # Check if we actually have the file Bob wants
                        if os.path.exists(filepath):
                            conn.sendall("SENDING".encode('utf-8')) # Send ACK
                            
                            # Read the saved file and send it to Bob
                            with open(filepath, 'rb') as f:
                                while True:
                                    chunk_data = f.read(4096)
                                    if not chunk_data: break
                                    conn.sendall(chunk_data)
                            print(f"[Peer {port}] Sent {filepath} to Bob.")
                        else:
                            conn.sendall("ERROR_NOT_FOUND".encode('utf-8'))
                            
                except json.JSONDecodeError:
                    print(f"[Peer {port}] Invalid request received.")

if __name__ == "__main__":
    port_num = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    start_peer(port_num)