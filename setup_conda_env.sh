#!/bin/bash
# Setup script for creating conda environment for Key Character Liver project

# Path to conda installation
CONDA_PATH="$HOME/anaconda3.7"

# Check if conda exists
if [ ! -f "$CONDA_PATH/bin/conda" ]; then
    echo "Error: Conda not found at $CONDA_PATH/bin/conda"
    echo "Please verify the conda installation path."
    exit 1
fi

# Initialize conda for bash shell
source "$CONDA_PATH/etc/profile.d/conda.sh"

# Environment name
ENV_NAME="key_char_liver"

echo "Creating conda environment: $ENV_NAME"
echo "Using conda from: $CONDA_PATH"

# Create environment from environment.yml
"$CONDA_PATH/bin/conda" env create -f environment.yml

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Environment '$ENV_NAME' created successfully!"
    echo ""
    echo "To activate the environment, run:"
    echo "  source $CONDA_PATH/etc/profile.d/conda.sh"
    echo "  conda activate $ENV_NAME"
    echo ""
    echo "Or use the activate script:"
    echo "  source activate_env.sh"
else
    echo ""
    echo "✗ Failed to create environment. Please check the error messages above."
    exit 1
fi
