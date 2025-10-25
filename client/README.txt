Online Chat Room - Client
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
How to Run the Client (Linux)
-------------------------

1. Open a terminal window.
2. Navigate to the folder where client.py is located. Example:
   cd ~/Desktop/client
3. Run the client with:
   python3 client.py localhost 5000

4. Follow the prompts:
   Username: your_username
   Password: your_password

   If the username is new, you’ll be automatically registered.
   If it already exists, your password will be verified.

-------------------------
Available Operations
-------------------------
Once logged in, you can use:

PM → Send a public message to everyone
DM → Send a private message to one specific user
EX → Exit the chat

-------------------------
Features
-------------------------
✓ JSON-based communication.
✓ Supports multiple simultaneous clients.
✓ Public messaging (PM) and direct messaging (DM).
✓ Dynamic online user list updates every login, logout, or every 30 seconds.
✓ Receives real-time broadcast and direct messages.
✓ Clean exit with 'EX'.

-------------------------
Testing Multiple Clients
-------------------------
1. Open multiple terminal windows.
2. In each, run:
   python3 client.py localhost 5000
3. Login as different users.
4. Use PM to chat publicly or DM to message privately.
5. When exiting (EX), other users will see a leave message and updated user list.

-------------------------
Troubleshooting
-------------------------
- Make sure the server is running before starting the client.
- Ensure the host (e.g., localhost) and port (e.g., 5000) match the server’s values.
- If "Connection refused" appears, confirm the server is active and reachable.
