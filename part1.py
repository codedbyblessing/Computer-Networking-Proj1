import socket
import json
import os

# Configuration for data type
CHUNKER_SIZE = 1024 * 1024  # 1mb in chunks
PEERS = [('127.0.0.1', 5001), ('127.0.0.1', 5002)] # ip address and the port numbers
TRACKER_ADDR = ('127.0.0.1', 6000)

def alice_share_file(file_path):
    file_name = os.path.basename(file_path)
    chunk_locations = {} #dictionary for mapping chunk to the address in the network
    #address is needed to have integrity in peer to peer sharing across the network, the chunk id is for ordering of packets/chunks

    # File Chunking 
    print(f"--- Step 1: File Chunking {file_name} ---") #print statements for debugging, we dont need to keep them, could simplify to {file_name}
    chunks = []
    with open(file_path, 'rb') as f: #we need to read the data into binary to send accross the network and python has its own terminology for reading binary
        #we eventually need to use wb to write binary, this would be on the other end in reconstruction, not for Alice.
        chunk_idx = 0
        while True:
            data = f.read(CHUNKER_SIZE)
            if not data: break
            chunks.append(data) #here we are adding the chunk as long as there are some remianing, then the index increments to add the next chunk of data
            chunk_idx += 1
    
    # Peer Notification & Distribution 
    print(f"--- Step 2: Distributing to {len(PEERS)} Peers ---") 
    for i, chunk_data in enumerate(chunks):
        # P2P integrity
        target_peer = PEERS[i % len(PEERS)]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: #TCP connection
                s.connect(target_peer)
                # Mandatory Notification to alert that data is being sent, must happen before connections are stabilized in TCP
                # this is needed to make sure chunks are being sent correctly in the network so the other peer can expect them 
                notification = json.dumps({
                    "type": "new_chunk",
                    "filename": file_name,
                    "chunk_id": i,
                    "size": len(chunk_data)
                })
                s.sendall(notification.encode('utf-8')) #utf , need to process bytes to readable format in the notifcation 

                # acknowledgemnt as discussed in class, aka ACK
                s.sendall(chunk_data)
                
                chunk_locations[i] = target_peer[0] # Store Peer IP for the tracker use
                print(f"Sent chunk {i} to {target_peer}")
        except Exception as e:
            print(f"Error sending chunk {i} to {target_peer}: {e}") #error handling is needed when testing the actual code

    # 3. Tracker Registration
    print("--- Step 3 Tracking: ---") #debugging might not keep 
    register_with_tracker(file_name, len(chunks), chunk_locations)

def register_with_tracker(name, total, locations):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: #TCP connection
            s.connect(TRACKER_ADDR)
            registration_data = {
                "type": "REGISTER_FILE",
                "file_name": name,
                "total_chunks": total,
                "locations": locations # The map is needed for hte chunks to arrive to the correct place in the network in the recieving end
            }
            s.sendall(json.dumps(registration_data).encode('utf-8'))
            print("Successfully registered with Tracker.") #notification, idk if we need another ACK or not, assuming each chunk has its own ACK
    except Exception as e:
        print(f"Tracker registration failed: {e}") #good practice in programming again






if __name__ == "__main__":
    alice_share_file("randomvid.mp4") # we could use a song too I dont mind but idk how this code change if we use a image or txt