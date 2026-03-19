import socket
import json
import struct

HOST = '0.0.0.0'
PORT = 6000

# chunk info storage
tracker_db = {}


def receive_bytes_from(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def receive_json_from(sock):
    raw_len = receive_bytes_from(sock, 4)
    if not raw_len:
        return None

    msg_len = struct.unpack('!I', raw_len)[0]
    data = receive_bytes_from(sock, msg_len)
    return json.loads(data.decode('utf-8'))


def send_json(sock, data):
    encoded = json.dumps(data).encode('utf-8')
    sock.sendall(struct.pack('!I', len(encoded)))
    sock.sendall(encoded)


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

            tracker_db[file_name] = {
                "total_chunks": total_chunks,
                "locations": locations
            }

            print(f"Tracker: Registered {file_name}")
            print(f"# chunks: {total_chunks}")
            for cid, info in locations.items():
                print(f"Chunk {cid}: {info['ip']}:{info['port']} ({info['size']} bytes)")

        elif msg_type == "GET_FILE":
            file_name = request["file_name"]

            if file_name in tracker_db:
                response = {
                    "status": "OK",
                    "data": tracker_db[file_name]
                }
            else:
                response = {
                    "status": "ERROR",
                    "message": "File not found"
                }

            send_json(conn, response)

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