#!/bin/bash
# Run validation in background

cd /home/singam2/KEY_CHAR/Key_char_liver

echo "Starting validation in background..."
echo "Logs will be saved to: validation_nihms.log"

# Run validation script in background with nohup
nohup python run_validation_nihms.py > validation_nihms.log 2>&1 &

# Get the process ID
PID=$!
echo "Validation started with PID: $PID"
echo "Monitor progress with: tail -f validation_nihms.log"
echo "Check if running: ps -p $PID"
echo ""
echo "To stop: kill $PID"
