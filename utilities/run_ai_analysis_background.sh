#!/bin/bash
# Run AI analysis for Acetaminophen in background (first step before validation)

cd /home/singam2/KEY_CHAR/Key_char_liver

CHEMICAL="Acetaminophen"
MODELS="llama3.2,mixtral"

echo "Starting AI analysis for $CHEMICAL in background..."
echo "This will take 30-60 minutes depending on number of abstracts"
echo "Logs will be saved to: acetaminophen_analysis.log"

# Create Python script to run analysis
cat > /tmp/run_analysis_acetaminophen.py << 'EOF'
import sys
sys.path.insert(0, '/home/singam2/KEY_CHAR/Key_char_liver')

from app import analyze_chemical
import traceback

try:
    print("Starting analysis...")
    result = analyze_chemical(
        chemical_name="Acetaminophen",
        model_names=["llama3.2", "mixtral"],
        enable_rob=True,
        enable_certainty=True
    )
    print("✅ Analysis complete!")
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
    sys.exit(1)
EOF

# Run in background with nohup
nohup python /tmp/run_analysis_acetaminophen.py > acetaminophen_analysis.log 2>&1 &

PID=$!
echo "Analysis started with PID: $PID"
echo ""
echo "Monitor progress with:"
echo "  tail -f acetaminophen_analysis.log"
echo ""
echo "Check if running:"
echo "  ps -p $PID"
echo ""
echo "To stop:"
echo "  kill $PID"
echo ""
echo "Once analysis completes, run validation with:"
echo "  python run_validation_nihms.py"
