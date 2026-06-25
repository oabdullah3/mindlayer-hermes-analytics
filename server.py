#!/usr/bin/env python3
"""
DEPRECATED: Hermes Analytics Server has moved to remoteend/server.py.
This wrapper exists for backward compatibility and will be removed
in a future release.

For the local single-user server, use userend/server.py (started by
the /hermes-snapshot-analytics slash command).
"""
import sys
import os

sys.stderr.write("[DEPRECATED] server.py moved to remoteend/server.py\n")
sys.path.insert(0, os.path.dirname(__file__))

from remoteend.server import app, PORT

if __name__ == "__main__":
    print(f"[hermes-analytics] Starting multi-user server on port {PORT} "
          f"(via remoteend/server.py)")
    app.run(host="0.0.0.0", port=PORT, debug=False)
