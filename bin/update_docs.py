#!/usr/bin/env python3
import subprocess


def main():
    print("Updating documentation...")
    # Rebuild code map
    try:
        subprocess.run(["python3", "tools/ast-bridge/code_mapper.py", "."], check=True)
        print("Symbol map updated.")
    except Exception as e:
        print(f"Failed to update symbol map: {e}")

    # Additional doc sync logic could go here
    print("Documentation sync complete.")

if __name__ == "__main__":
    main()
