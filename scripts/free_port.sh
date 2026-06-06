#!/usr/bin/env bash
# Print an available TCP port for atelier to run a server on, chosen so it can
# NEVER collide with the user's own dev server. It deliberately skips the common
# framework defaults (3000 / 5173 / 4321 / 8080 / ...), so starting atelier's own
# instance can't kill or fight a dev server the user already has running.
#
# Usage:
#   free_port.sh            # first free port from 43110 upward, skipping defaults
#   free_port.sh 47000      # start scanning from a port you prefer
#
# Pair it with detect_server.sh: REUSE a running server if one is up; only start
# your own — on this free port — when nothing is running or you need isolation.
COMMON="3000 3001 5173 5174 4321 4322 8080 8000 4200 5000 1313 8788 3333 4000 9000 3030"
START="${1:-43110}"
python3 - "$START" "$COMMON" <<'PY'
import socket, sys
start = int(sys.argv[1])
common = {int(p) for p in sys.argv[2].split()}
def free(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p))
        return True
    except OSError:
        return False
    finally:
        s.close()
for p in range(start, start + 500):
    if p not in common and free(p):
        print(p)
        sys.exit(0)
sys.exit(1)
PY
