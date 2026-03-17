import socket
import json
import os

# Configuration for data type
CHUNKER_SIZE = 1024 * 1024  # 1mb in chunks
PEERS = [('127.0.0.1', 5001), ('127.0.0.1', 5002)] # ip address and the port numbers
TRACKER_ADDR = ('127.0.0.1', 6000)

def alice_share_file(file_path):
    file_name = os.path.basename(file_path)
    chunk_locations = {} # dictionary for mapping chunk to the address in the network

    # File Chunking 
    print(f"--- Step 1: File Chunking {file_name} ---") 
    chunks = []
    with open(file_path, 'rb') as f: 
        chunk_idx = 0
        while True:
            data = f.read(CHUNKER_SIZE)
            if not data: break
            chunks.append(data) 
            chunk_idx += 1
    
    # Peer Notification & Distribution 
    print(f"--- Step 2: Distributing to {len(PEERS)} Peers ---") 
    for i, chunk_data in enumerate(chunks):
        # P2P integrity
        target_peer = PEERS[i % len(PEERS)]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # TCP connection
                s.connect(target_peer)
                
                # Mandatory Notification
                notification = json.dumps({
                    "type": "new_chunk",
                    "filename": file_name,
                    "chunk_id": i,
                    "size": len(chunk_data)
                })
                s.sendall(notification.encode('utf-8')) 

                # FIX 1: Wait for the ACK from the peer before sending data!
                # This prevents the JSON header and binary data from blending together.
                ack = s.recv(1024).decode('utf-8')
                
                if ack == "READY":
                    s.sendall(chunk_data)
                    
                    # FIX 2: Store both the IP and the Port so Bob knows exactly where to go!
                    chunk_locations[i] = {"ip": target_peer[0], "port": target_peer[1]} 
                    print(f"Sent chunk {i} to {target_peer}")
                else:
                    print(f"Peer {target_peer} rejected the chunk.")
                    
        except Exception as e:
            print(f"Error sending chunk {i} to {target_peer}: {e}") 

    # 3. Tracker Registration
    print("--- Step 3 Tracking: ---") 
    register_with_tracker(file_name, len(chunks), chunk_locations)

def register_with_tracker(name, total, locations):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: 
            s.connect(TRACKER_ADDR)
            registration_data = {
                "type": "REGISTER_FILE",
                "file_name": name,
                "total_chunks": total,
                "locations": locations 
            }
            s.sendall(json.dumps(registration_data).encode('utf-8'))
            
            # FIX 3: Good practice to wait for Tracker's ACK as well
            tracker_ack = s.recv(1024).decode('utf-8')
            print(f"Tracker responded: {tracker_ack} \n") 
            
    except Exception as e:
        print(f"Tracker registration failed: {e}") 

if __name__ == "__main__":
    # Note: Because this reads the whole file into memory (the 'chunks' list), 
    # keep your test video relatively small (e.g., under 50MB) so you don't crash your RAM!
    alice_share_file("/Users/solomon/Downloads/Computer-Networking-Proj1-main/Lab Report - Black Horse.pdf")