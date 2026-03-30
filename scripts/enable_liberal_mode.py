"""
Quick script to enable liberal prompt mode for better KC detection
Run this before analyzing chemicals where mechanisms are being missed

This script sets environment variables that persist across Python sessions.
"""

import os
import sys


def set_prompt_mode(mode: str, enhanced: bool = True):
    """Set prompt mode via environment variable"""
    os.environ["PROMPT_MODE"] = mode
    os.environ["ENABLE_ENHANCED_PROMPTS"] = str(enhanced)

    # Also write to a .env file for persistence (optional)
    env_file = ".prompt_mode"
    try:
        with open(env_file, 'w') as f:
            f.write(f"PROMPT_MODE={mode}\n")
            f.write(f"ENABLE_ENHANCED_PROMPTS={enhanced}\n")
        print(f"✅ Configuration saved to {env_file}")
    except Exception as e:
        print(f"⚠️  Could not write to {env_file}: {e}")
        print("   (This is okay - environment variable is set for this session)")

def enable_liberal_mode():
    """Enable liberal prompt mode for more permissive KC detection"""
    set_prompt_mode("liberal", enhanced=True)
    print("✅ Liberal prompt mode enabled!")
    print("   This mode is more permissive and will detect mechanisms even when described indirectly.")
    print("\n   Prompt modes available:")
    print("   - 'standard': Original prompts (strict)")
    print("   - 'enhanced': Enhanced prompts with synonyms (default)")
    print("   - 'liberal': Very permissive prompts (current)")
    print("\n   This setting persists for this terminal session.")
    print("   To change mode, run this script again with a different mode.")

def enable_enhanced_mode():
    """Enable enhanced prompt mode (default)"""
    set_prompt_mode("enhanced", enhanced=True)
    print("✅ Enhanced prompt mode enabled (default)")

def enable_standard_mode():
    """Enable standard prompt mode"""
    set_prompt_mode("standard", enhanced=False)
    print("✅ Standard prompt mode enabled")

def load_from_file():
    """Load prompt mode from .prompt_mode file if it exists"""
    env_file = ".prompt_mode"
    if os.path.exists(env_file):
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
        except Exception as e:
            print(f"⚠️  Could not read {env_file}: {e}")
    return False

if __name__ == "__main__":
    # Try to load from file first
    load_from_file()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "liberal":
            enable_liberal_mode()
        elif mode == "enhanced":
            enable_enhanced_mode()
        elif mode == "standard":
            enable_standard_mode()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python enable_liberal_mode.py [liberal|enhanced|standard]")
            sys.exit(1)
    else:
        # Default to liberal for Acetaminophen issues
        enable_liberal_mode()
        print("\n💡 Tip: Run this before starting app.py for better Acetaminophen detection")
        print("   Or run: python enable_liberal_mode.py enhanced  # to switch back")
