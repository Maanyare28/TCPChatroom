import socket
import threading
import json
import sys
import time

stop_event = threading.Event()   # shared flag to stop threads safely


def show_prompt():
    """Re-display the operation prompt after any incoming message."""
    if not stop_event.is_set():
        print("\nEnter operation (PM, DM, EX): ", end="", flush=True)


def receive_messages(sock, username):
    """Receive messages from server continuously with buffered JSON parsing."""
    buffer = ""
    while not stop_event.is_set():
        try:
            data = sock.recv(4096)
            if not data:
                print("Disconnected from server.")
                break

            buffer += data.decode('utf-8')
            while True:
                try:
                    msg, idx = json.JSONDecoder().raw_decode(buffer)
                    buffer = buffer[idx:].lstrip()

                    msg_type = msg.get("type", "")
                    sender = msg.get("from", "")

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
                    # incomplete JSON, wait for more data
                    break
        except OSError:
            break
        except Exception as e:
            print("Receiver crashed:", e)
            break


def send_messages(sock, username):
    """Handle user input and send JSON commands to server."""
    while not stop_event.is_set():
        cmd = input("\nEnter operation (PM, DM, EX): ").strip().upper()
        if cmd == "PM":
            msg = input("Enter message: ")
            sock.send(json.dumps({
                "command": "pm",
                "message": msg
            }).encode('utf-8'))

        elif cmd == "DM":
            target = input("Enter recipient username: ")
            msg = input("Enter message: ")
            sock.send(json.dumps({
                "command": "dm",
                "to": target,
                "message": msg
            }).encode('utf-8'))

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


def login(sock):
    """Handle user login and verify response."""
    username = input("Username: ")
    password = input("Password: ")

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

            # Try to parse full JSON message
            msg, idx = json.JSONDecoder().raw_decode(buffer)
            buffer = buffer[idx:].lstrip()

            response = msg
            break
        except json.JSONDecodeError:
            # Incomplete JSON, keep waiting
            continue

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


def run_client(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print(f"Connected to {host}:{port}")

    username = login(sock)

    recv_thread = threading.Thread(target=receive_messages, args=(sock, username), daemon=True)
    recv_thread.start()
    time.sleep(0.3)

    try:
        send_messages(sock, username)
    except Exception as e:
        print("Error in sending:", e)
    finally:
        print("Client shutting down.")
        stop_event.set()
        try:
            sock.close()
        except:
            pass
        recv_thread.join(timeout=1)


if __name__ == "__main__":
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