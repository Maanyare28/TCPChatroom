import socket
import threading
import json
import os
import sys

USERS_FILE = 'users.txt'
active_clients = {}
lock = threading.Lock()
server_running = True


def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                if ':' in line:
                    u, p = line.strip().split(':', 1)
                    u, p = u.strip(), p.strip()
                    users[u] = p
    return users


def save_user(u, p):
    with open(USERS_FILE, 'a') as f:
        f.write(f"{u}:{p}\n")


def broadcast(message, exclude=None):
    """Send message to all connected clients."""
    data = json.dumps(message).encode('utf-8')
    with lock:
        for user, conn in list(active_clients.items()):
            if user != exclude:
                try:
                    conn.sendall(data)
                except:
                    pass


def update_user_list():
    """Notify all clients of updated user list."""
    with lock:
        users = list(active_clients.keys())
    broadcast({"type": "user_list", "users": users})


def handle_client(conn, addr, users_db):
    """Thread for each client."""
    username = None
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                return
            msg = json.loads(data.decode('utf-8'))

            if msg.get("command") == "login":
                username = msg["username"].strip()
                password = msg["password"].strip()

                if username not in users_db:
                    users_db[username] = password
                    save_user(username, password)
                    conn.sendall(json.dumps(
                        {"type": "status", "message": "New user registered successfully."}
                    ).encode('utf-8'))
                elif users_db[username] != password:
                    conn.sendall(json.dumps(
                        {"type": "error", "message": "Invalid password."}
                    ).encode('utf-8'))
                    return
                else:
                    conn.sendall(json.dumps(
                        {"type": "status", "message": "Login successful."}
                    ).encode('utf-8'))

                with lock:
                    active_clients[username] = conn
                update_user_list()
                break

        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = json.loads(data.decode('utf-8'))
            cmd = msg.get("command")

            if cmd == "pm":
                broadcast({
                    "type": "broadcast",
                    "from": username,
                    "message": msg["message"]
                })
            elif cmd == "dm":
                target = msg["to"]
                message = msg["message"]
                with lock:
                    target_conn = active_clients.get(target)
                if target_conn:
                    target_conn.sendall(json.dumps({
                        "type": "direct",
                        "from": username,
                        "message": message
                    }).encode('utf-8'))
                    conn.sendall(json.dumps({
                        "type": "status",
                        "message": f"DM sent to {target}."
                    }).encode('utf-8'))
                else:
                    conn.sendall(json.dumps({
                        "type": "error",
                        "message": f"User {target} not found."
                    }).encode('utf-8'))
            elif cmd == "ex":
                conn.sendall(json.dumps({
                    "type": "status",
                    "message": "Exiting chat..."
                }).encode('utf-8'))
                break
    except (ConnectionResetError, json.JSONDecodeError):
        pass
    finally:
        if username:
            with lock:
                active_clients.pop(username, None)
            update_user_list()
        try:
            conn.close()
        except:
            pass
        print(f"Connection closed: {addr}")


def server_console(stop_event):
    """Allows the admin to shut down the server with EX."""
    while not stop_event.is_set():
        cmd = input().strip().upper()
        if cmd == "EX":
            print("\n[Server Console] Shutting down server...")
            broadcast({"type": "status", "message": "Server is shutting down..."})
            stop_event.set()
            break
        else:
            print("Unknown command. Type 'EX' to stop the server.")


def run_server(host, port):
    users_db = load_users()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(10)
    server_sock.settimeout(1.0)

    print(f"Server listening on {host}:{port}")
    print("Type 'EX' to stop the server.\n")

    stop_event = threading.Event()
    console_thread = threading.Thread(target=server_console, args=(stop_event,), daemon=True)
    console_thread.start()

    try:
        while not stop_event.is_set():
            try:
                conn, addr = server_sock.accept()
                print(f"New connection: {addr}")
                threading.Thread(target=handle_client, args=(conn, addr, users_db), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break  # socket closed, exit loop
    finally:
        stop_event.set()
        try:
            server_sock.close()
        except:
            pass

        with lock:
            for conn in list(active_clients.values()):
                try:
                    conn.close()
                except:
                    pass
            active_clients.clear()

        print("Server closed.")
        console_thread.join(timeout=1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python server.py <ip_address> <port>")
        sys.exit(1)

    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    run_server(host, port)