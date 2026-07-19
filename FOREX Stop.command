#!/bin/bash
# FOREX Trader — Stop
cd "$(dirname "$0")"
PIDS=$(lsof -ti:8888 2>/dev/null)
if [ -z "$PIDS" ]; then
    echo "FOREX Trader is not running."
else
    echo "Stopping FOREX Trader (PID $PIDS)..."
    kill $PIDS 2>/dev/null
    sleep 1
    echo "Stopped."
fi
