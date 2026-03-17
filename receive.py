import socket
import json
import os

TRACKER_ADDR = ('127.0.0.1', 6000)

def bob_download_file(file_name):
    print(f"--- Step 1: Asking Tracker for {file_name} ---")
    
    # 1. Ask the tracker for the chunk locations
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(TRACKER_ADDR)
            query = json.dumps({
                "type": "QUERY_FILE",
                "file_name": file_name
            })
            s.sendall(query.encode('utf-8'))
            
            # Receive the dictionary of locations from the tracker
            response = s.recv(4096).decode('utf-8')
            tracker_data = json.loads(response)
            
            if tracker_data.get("status") != "FOUND":
                print("Tracker could not find the file.")
                return
            
            chunk_locations = tracker_data.get("locations")
            total_chunks = tracker_data.get("total_chunks")
            print(f"Tracker found {total_chunks} chunks. Locations: {chunk_locations}")
            
    except Exception as e:
        print(f"Failed to communicate with Tracker: {e}")
        return

    print(f"\n--- Step 2: Downloading Chunks from Peers ---")
    reconstructed_file = "reconstructed_" + file_name
    
    # 2. Open the new file we are about to build in "wb" (write binary) mode
    with open(reconstructed_file, 'wb') as outfile:
        
        # We must download in order (0 to total_chunks - 1) so the video doesn't get scrambled!
        for i in range(total_chunks):
            # JSON keys are converted to strings when sent over the network
            str_i = str(i) 
            if str_i not in chunk_locations:
                print(f"Missing location for chunk {i}!")
                return
            
            peer_ip = chunk_locations[str_i]["ip"]
            peer_port = chunk_locations[str_i]["port"]
            
            print(f"Downloading chunk {i} from {peer_ip}:{peer_port}...")
            
            # 3. Connect to the specific peer and request the chunk
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ps:
                    ps.connect((peer_ip, peer_port))
                    
                    # Send a JSON request asking for this specific chunk
                    request = json.dumps({
                        "type": "request_chunk",
                        "file_name": file_name,
                        "chunk_id": i
                    })
                    ps.sendall(request.encode('utf-8'))
                    
                    # Wait for the peer to ACK that it found the file and is ready
                    ack = ps.recv(1024).decode('utf-8')
                    if ack == "SENDING":
                        # Receive the binary chunk and write it directly to our final file
                        while True:
                            packet = ps.recv(4096)
                            if not packet: break # The peer closed the connection, chunk is done
                            outfile.write(packet)
                        print(f"Chunk {i} downloaded and written!")
                    else:
                        print(f"Peer {peer_port} refused to send chunk {i}. It said: {ack}")
                        
            except Exception as e:
                print(f"Error downloading chunk {i}: {e}")
                return
                
    print(f"\n--- Step 3: Success! ---")
    print(f"File successfully reassembled as: {reconstructed_file}")

if __name__ == "__main__":
    # The file name can be changed 
    bob_download_file("Lab Report - Black Horse.pdf")