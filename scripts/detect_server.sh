#!/usr/bin/env bash
# Detect an already-running dev server so atelier doesn't start a second one.
# Probes common dev-server ports (override by passing your own) and prints the
# first reachable http URL, or nothing. Use BEFORE serving/starting anything in a
# visual review.
#
# Usage:
#   detect_server.sh                 # probe the common ports
#   detect_server.sh 3000 8080 9001  # probe specific ports
PORTS="${*:-3000 3001 5173 5174 4321 8080 8000 4200 5000 1313 8788 3333 4000}"
for p in $PORTS; do
  if curl -fsS -o /dev/null --max-time 1 "http://localhost:$p/" 2>/dev/null; then
    echo "http://localhost:$p"
    exit 0
  fi
done
exit 1   # nothing running — ask the user to run it, or render the component in isolation
