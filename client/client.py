import socket
import threading
import json
import sys
import time

# Global event flag used to safely stop both sender and receiver threads
stop_event = threading.Event()


# -----------------------------
# Helper function to re-display input prompt
# -----------------------------
def show_prompt():
    """Re-display the operation prompt after receiving any message."""
    if not stop_event.is_set():
        print("\nEnter operation (PM, DM, EX): ", end="", flush=True)


# -----------------------------
# Function to receive messages from the server
# -----------------------------
def receive_messages(sock, username):
    """
    Continuously listens for messages sent from the server.
    Uses a buffer to handle cases where multiple JSON messages
    arrive together or a single message arrives in chunks.
    """
    buffer = ""
    while not stop_event.is_set():
        try:
            data = sock.recv(4096)
            if not data:
                print("Disconnected from server.")
                break

            # Append new data to buffer and try to parse complete JSON messages
            buffer += data.decode('utf-8')
            while True:
                try:
                    # Decode one JSON message from the buffer
                    msg, idx = json.JSONDecoder().raw_decode(buffer)
                    buffer = buffer[idx:].lstrip()

                    msg_type = msg.get("type", "")
                    sender = msg.get("from", "")

                    # Display different message types accordingly
                    if msg_type == "broadcast":
                        print(f"\n[Public] {sender}: {msg['message']}")
                        if sender != username:
                            show_prompt()

                    elif msg_type == "direct":
                        print(f"\n[DM] {sender}: {msg['message']}")
                        if sender != username:
                            show_prompt()

                    elif msg_type == "user_list":
                        print(f"\n[Online Users]: {', '.join(msg['users'])}")
                        show_prompt()

                    elif msg_type == "status":
                        print(f"[Server]: {msg['message']}")
                        show_prompt()

                    elif msg_type == "error":
                        print(f"[Error]: {msg['message']}")
                        show_prompt()

                except json.JSONDecodeError:
                    # JSON incomplete → wait for more data
                    break

        except OSError:
            # Socket closed, stop the receiver
            break
        except Exception as e:
            print("Receiver crashed:", e)
            break


# -----------------------------
# Function to send messages to the server
# -----------------------------
def send_messages(sock, username):
    """
    Handles user input in a separate thread.
    Allows the user to send public messages (PM),
    direct messages (DM), or exit (EX).
    """
    while not stop_event.is_set():
        cmd = input("\nEnter operation (PM, DM, EX): ").strip().upper()

        # Public Message
        if cmd == "PM":
            msg = input("Enter message: ")
            sock.send(json.dumps({
                "command": "pm",
                "message": msg
            }).encode('utf-8'))

        # Direct Message
        elif cmd == "DM":
            target = input("Enter recipient username: ")
            msg = input("Enter message: ")
            sock.send(json.dumps({
                "command": "dm",
                "to": target,
                "message": msg
            }).encode('utf-8'))

        # Exit Command
        elif cmd == "EX":
            sock.send(json.dumps({"command": "ex"}).encode('utf-8'))
            print("Exiting...")
            stop_event.set()
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            sock.close()
            break

        else:
            print("Invalid command. Use PM, DM, or EX.")


# -----------------------------
# Login Function
# -----------------------------
def login(sock):
    """
    Handles login or registration.
    Sends username and password to the server,
    then waits for a JSON response.
    """
    username = input("Username: ")
    password = input("Password: ")

    # Send login request to server
    sock.send(json.dumps({
        "command": "login",
        "username": username.strip(),
        "password": password.strip()
    }).encode('utf-8'))

    buffer = ""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("Connection closed by server.")
                sys.exit(1)

            buffer += data.decode('utf-8')

            # Try to decode a full JSON message
            msg, idx = json.JSONDecoder().raw_decode(buffer)
            buffer = buffer[idx:].lstrip()
            response = msg
            break

        except json.JSONDecodeError:
            # Wait for complete message
            continue

    # Process server response
    if response.get("type") == "error":
        print(f"[Server]: {response.get('message')}")
        sock.close()
        sys.exit(1)
    elif response.get("type") == "status":
        print(f"[Server]: {response.get('message')}")
        return username
    else:
        print("Unexpected response from server.")
        sock.close()
        sys.exit(1)


# -----------------------------
# Main function to start the client
# -----------------------------
def run_client(host, port):
    """Connect to the server, handle login, and start communication threads."""
    # Create TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print(f"Connected to {host}:{port}")

    # Perform login
    username = login(sock)

    # Start receiver thread
    recv_thread = threading.Thread(target=receive_messages, args=(sock, username), daemon=True)
    recv_thread.start()

    # Small delay to ensure receiver thread starts first
    time.sleep(0.3)

    # Handle user input (main thread)
    try:
        send_messages(sock, username)
    except Exception as e:
        print("Error in sending:", e)
    finally:
        # Graceful shutdown
        print("Client shutting down.")
        stop_event.set()
        try:
            sock.close()
        except:
            pass
        recv_thread.join(timeout=1)


# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    # Check proper usage
    if len(sys.argv) != 3:
        print("Usage: python client.py <server_ip> <port>")
        sys.exit(1)

    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    run_client(host, port)
