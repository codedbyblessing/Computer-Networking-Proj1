import socket
import json

# This dictionary will act as our central database
# Format will look like: {"randomvid.mp4": {"total_chunks": 4, "locations": {"0": {"ip": "127.0.0.1", "port": 5001}, ...}}}
tracker_database = {}

def start_tracker():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 6000))
        s.listen()
        print("Tracker listening on port 6000...")
        
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    continue
                
                try:
                    request = json.loads(data)
                    req_type = request.get("type")
                    
                    if req_type == "REGISTER_FILE":
                        # ALICE IS UPLOADING
                        file_name = request.get("file_name")
                        tracker_database[file_name] = {
                            "total_chunks": request.get("total_chunks"),
                            "locations": request.get("locations")
                        }
                        print(f"\n[Tracker] Registered file: {file_name}")
                        conn.sendall("TRACKER_ACK_SUCCESS".encode('utf-8'))
                        
                    elif req_type == "QUERY_FILE":
                        # BOB IS DOWNLOADING
                        file_name = request.get("file_name")
                        print(f"\n[Tracker] Bob is querying for: {file_name}")
                        
                        if file_name in tracker_database:
                            response = {
                                "status": "FOUND",
                                "total_chunks": tracker_database[file_name]["total_chunks"],
                                "locations": tracker_database[file_name]["locations"]
                            }
                        else:
                            response = {"status": "NOT_FOUND"}
                            
                        conn.sendall(json.dumps(response).encode('utf-8'))
                        
                except json.JSONDecodeError:
                    print("[Tracker] Received invalid JSON request.")

if __name__ == "__main__":
    start_tracker()