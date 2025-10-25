Online Chat Room - Server
-------------------------

Language: Python 3
Protocol: TCP (Transmission Control Protocol)
Message Format: JSON
Platform: Linux (tested on Ubuntu/Debian-based distros)

-------------------------
Requirements
-------------------------
- Python 3.7 or higher
- No external libraries needed (uses only Python standard library)

-------------------------
How to Run the Server (Linux)
-------------------------

1. Open a terminal window.
2. Navigate to the folder where server.py is located. Example:
   cd ~/Desktop/server
3. Start the server with:
   python3 server.py localhost 5000

You should see:
   Server listening on localhost:5000
   Type 'EX' to stop the server.

4. To stop the server at any time, type:
   EX
   and press Enter.

-------------------------
What the Server Does
-------------------------
✓ Listens for client connections on the specified host and port.
✓ Registers new users in users.txt (automatically created if missing).
✓ Verifies returning users' credentials.
✓ Handles multiple clients simultaneously (multithreading).
✓ Forwards public messages (PM) to all clients.
✓ Sends direct messages (DM) to specific recipients.
✓ Updates the list of active users dynamically on login, logout, or every 30 seconds.
✓ Broadcasts join/leave notifications.
✓ Gracefully shuts down on the 'EX' command.

-------------------------
Server Files
-------------------------
- server.py: Main server program.
- users.txt: Stores registered usernames and passwords (auto-created).

-------------------------
Troubleshooting
-------------------------
- Make sure no other program is using the same port (e.g., 5000).
- If you get "Address already in use", wait a few seconds or choose another port.
- Ensure clients are using the same host and port as the server.
