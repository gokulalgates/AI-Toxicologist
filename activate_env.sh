#!/bin/bash
# Script to activate the conda environment for Key Character Liver project

# Path to conda installation
CONDA_PATH="$HOME/anaconda3.7"

# Environment name
ENV_NAME="key_char_liver"

# Check if conda exists
if [ ! -f "$CONDA_PATH/bin/conda" ]; then
    echo "Error: Conda not found at $CONDA_PATH/bin/conda"
    echo "Please verify the conda installation path."
    exit 1
fi

# Initialize conda for bash shell
source "$CONDA_PATH/etc/profile.d/conda.sh"

# Activate environment
conda activate "$ENV_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Activated conda environment: $ENV_NAME"
    echo "Python version: $(python --version)"
    echo "Python path: $(which python)"
else
    echo "✗ Failed to activate environment. Make sure it exists by running:"
    echo "  bash setup_conda_env.sh"
    exit 1
fi
