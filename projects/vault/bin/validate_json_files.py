import argparse
import json
import os
import glob

def is_valid_json(file_path):
    """Checks if a file contains valid JSON."""
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except json.JSONDecodeError:
        return False

def main():
    """Parses arguments and checks JSON files in a directory."""
    parser = argparse.ArgumentParser(description='Check if JSON files in a directory are valid.')
    parser.add_argument('-d','--directory', help='The directory containing the JSON files.', default="./config/json_workspaces")
    parser.add_argument('-w', '--allow_file_regex', help='What files to include', default="**/*.json")
    args = parser.parse_args()

    invalid_files = []
    
    for file in glob.iglob(f"./{args.directory}/{args.allow_file_regex}", recursive=True, include_hidden=True):
        if os.path.isdir(file):
            continue
        else:
            if not is_valid_json(file):
                invalid_files.append(file)
    if invalid_files:
        print(f"The following JSON files are invalid:")
        for filename in invalid_files:
            print(f"  - {filename}")
    else:
        print("All JSON files in the directory are valid.")

if __name__ == '__main__':
    main()