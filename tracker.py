import socket
from network_utils import send_json, receive_json_from

HOST = '0.0.0.0'
PORT = 6000

tracker_database = {} # chunk info storage
peers = set() # list of peers

def handle_client(conn, addr):
    try:
        request = receive_json_from(conn)
        if not request:
            return

        msg_type = request.get("type")

        if msg_type == "NEW_FILE":
            file_name = request["file_name"]
            total_chunks = request["total_chunks"]
            locations = request["locations"]

            # Normalize key data type to strings, important for consistency  
            normalized_locations = {str(k): v for k, v in locations.items()}

            tracker_database[file_name] = {
                "total_chunks": total_chunks,
                "locations": normalized_locations
            }

            print(f"Tracker: Registered {file_name}")
            print(f"# chunks: {total_chunks}")
            for cid, info in locations.items():
                print(f"Chunk {cid}: {info['ip']}:{info['port']} ({info['size']} bytes)")

        elif msg_type == "GET_FILE":
            file_name = request["file_name"]

            if file_name in tracker_database:
                response = {
                    "status": "OK",
                    "data": tracker_database[file_name]
                }
            else:
                response = {
                    "status": "ERROR",
                    "message": "File not found"
                }

            send_json(conn, response)

        elif msg_type == "REGISTER_PEER":
            ip = request["ip"]
            port = request["port"]

            peers.add((ip, port))

            print(f"Peer registered: {ip}:{port}")
            send_json(conn, {"status": "OK"})

        elif msg_type == "GET_PEERS":
            peer_list = [{"ip": ip, "port": port} for (ip, port) in peers]

            send_json(conn, {
                "status": "OK",
                "peers": peer_list
            })

    except Exception as e:
        print(f"Error handling client {addr}: {e}")

    finally:
        conn.close()


def init_tracker():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()

        print(f"Tracker running on port {PORT}")

        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    init_tracker()