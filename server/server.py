import socket
import threading
import json
import os
import sys

# File that stores user credentials (username:password)
USERS_FILE = 'users.txt'

# Dictionary of currently active clients {username: connection}
active_clients = {}

# Lock for thread-safe access to shared data structures
lock = threading.Lock()

# Flag used to indicate if the server is running
server_running = True


# -----------------------------
# Load users from users.txt
# -----------------------------
def load_users():
    """Load registered users from the users.txt file into a dictionary."""
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                # Each line has the format username:password
                if ':' in line:
                    u, p = line.strip().split(':', 1)
                    users[u.strip()] = p.strip()
    return users


# -----------------------------
# Save new user to users.txt
# -----------------------------
def save_user(u, p):
    """Register a new user by appending to users.txt."""
    with open(USERS_FILE, 'a') as f:
        f.write(f"{u}:{p}\n")


# -----------------------------
# Broadcast message to all clients
# -----------------------------
def broadcast(message, exclude=None):
    """Send a JSON-encoded message to all connected clients except 'exclude'."""
    data = json.dumps(message).encode('utf-8')
    with lock:
        for user, conn in list(active_clients.items()):
            if user != exclude:
                try:
                    conn.sendall(data)
                except:
                    # Ignore clients that have disconnected unexpectedly
                    pass


# -----------------------------
# Update all clients with the current active user list
# -----------------------------
def update_user_list():
    """Notify all clients of the updated list of online users."""
    with lock:
        users = list(active_clients.keys())

    # Send updated list to all clients
    broadcast({"type": "user_list", "users": users})

    # Display list in server console for admin visibility
    print(f"[Server] Active users: {', '.join(users) if users else '(none)'}")


# -----------------------------
# Handle each connected client
# -----------------------------
def handle_client(conn, addr, users_db):
    """Handle a single client's login, messaging, and logout process."""
    username = None
    try:
        # -----------------------------
        # LOGIN PHASE
        # -----------------------------
        while True:
            data = conn.recv(1024)
            if not data:
                return
            msg = json.loads(data.decode('utf-8'))

            # Process login command
            if msg.get("command") == "login":
                username = msg["username"].strip()
                password = msg["password"].strip()

                # New user registration
                if username not in users_db:
                    users_db[username] = password
                    save_user(username, password)
                    conn.sendall(json.dumps(
                        {"type": "status", "message": "New user registered successfully."}
                    ).encode('utf-8'))

                # Invalid password check
                elif users_db[username] != password:
                    conn.sendall(json.dumps(
                        {"type": "error", "message": "Invalid password."}
                    ).encode('utf-8'))
                    return

                # Existing user successfully logged in
                else:
                    conn.sendall(json.dumps(
                        {"type": "status", "message": "Login successful."}
                    ).encode('utf-8'))

                # Add user to active clients list
                with lock:
                    active_clients[username] = conn

                print(f"[Server] {username} connected from {addr}")
                broadcast({"type": "status", "message": f"{username} has joined the chat."})
                update_user_list()
                break  # Exit login phase

        # -----------------------------
        # MESSAGING PHASE
        # -----------------------------
        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = json.loads(data.decode('utf-8'))
            cmd = msg.get("command")

            # Public message to all clients
            if cmd == "pm":
                broadcast({
                    "type": "broadcast",
                    "from": username,
                    "message": msg["message"]
                })

            # Direct message to a specific user
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

            # Exit command
            elif cmd == "ex":
                conn.sendall(json.dumps({
                    "type": "status",
                    "message": "Exiting chat..."
                }).encode('utf-8'))
                break

    except (ConnectionResetError, json.JSONDecodeError):
        # Handle unexpected disconnects or invalid JSON
        pass

    finally:
        # -----------------------------
        # LOGOUT / CLEANUP PHASE
        # -----------------------------
        if username:
            # Remove from active clients
            with lock:
                active_clients.pop(username, None)

            # Notify others of departure
            broadcast({"type": "status", "message": f"{username} has left the chat."})
            update_user_list()
            print(f"[Server] {username} disconnected.")

        # Close the connection
        try:
            conn.close()
        except:
            pass


# -----------------------------
# Server console control thread
# -----------------------------
def server_console(stop_event):
    """Allows the admin to stop the server manually with 'EX'."""
    global server_running
    while not stop_event.is_set():
        cmd = input().strip().upper()
        if cmd == "EX":
            print("\n[Server Console] Shutting down server...")
            broadcast({"type": "status", "message": "Server is shutting down..."})
            stop_event.set()
            server_running = False
            break
        else:
            print("Unknown command. Type 'EX' to stop the server.")


# -----------------------------
# Main server function
# -----------------------------
def run_server(host, port):
    """Start the server, accept incoming client connections, and manage threads."""
    users_db = load_users()

    # Create and configure TCP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(10)
    server_sock.settimeout(1.0)

    print(f"Server listening on {host}:{port}")
    print("Type 'EX' to stop the server.\n")

    stop_event = threading.Event()

    # Thread to listen for admin console input
    console_thread = threading.Thread(target=server_console, args=(stop_event,), daemon=True)
    console_thread.start()

    try:
        # Continuously accept new client connections
        while not stop_event.is_set():
            try:
                conn, addr = server_sock.accept()
                print(f"[Server] New connection from {addr}")
                threading.Thread(
                    target=handle_client, args=(conn, addr, users_db), daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

    finally:
        # Clean shutdown
        stop_event.set()
        try:
            server_sock.close()
        except:
            pass

        # Close all active client sockets
        with lock:
            for conn in list(active_clients.values()):
                try:
                    conn.close()
                except:
                    pass
            active_clients.clear()

        print("[Server] Closed all connections.")
        console_thread.join(timeout=1)


# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 server.py <ip_address> <port>")
        sys.exit(1)

    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    run_server(host, port)
