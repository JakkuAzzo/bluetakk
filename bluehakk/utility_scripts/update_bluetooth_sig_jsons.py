import os
import re
import yaml
import json
import shutil
import subprocess

def convert_yaml_to_json(yaml_path, json_path, loader_cls=yaml.SafeLoader, log_file="bluetooth_sig_jsons.txt"):
    """
    Loads the YAML file using the specified loader and writes the data out as JSON.
    Also logs the JSON file path to a text file.
    """
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.load(f, Loader=loader_cls)
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Converted {yaml_path} -> {json_path}")
        # Append the json_path to the log file.
        with open(log_file, 'a') as lf:
            lf.write(json_path + "\n")
    except Exception as e:
        print(f"Error converting {yaml_path} to {json_path}: {e}")

def get_loader_for_file(yaml_path):
    """
    Determine which loader to use based on the file path.
    For files in a folder name containing "company_identifiers",
    use the HexStringLoader; otherwise, use the default SafeLoader.
    """
    if "company_identifiers" in yaml_path:
        class HexStringLoader(yaml.SafeLoader):
            pass

        def hex_int_constructor(loader, node):
            value = loader.construct_scalar(node)
            if re.match(r'^0[xX][0-9a-fA-F]+$', value):
                return value
            try:
                return int(value)
            except ValueError:
                return value

        HexStringLoader.add_constructor('tag:yaml.org,2002:int', hex_int_constructor)
        return HexStringLoader
    else:
        return yaml.SafeLoader

def main():
    # Define repository URL and directory names.
    repo_url = "https://bitbucket.org/bluetooth-SIG/public.git"
    base_yaml_dir = "bluetooth-SIG-public-2fb4976b994d"
    output_dir = "bluetooth-sig-public-jsons"
    log_file = "bluetooth_sig_jsons.txt"

    # Check for and update/clone the repository.
    if os.path.exists(base_yaml_dir):
        print(f"Repository folder '{base_yaml_dir}' exists. Pulling latest changes...")
        subprocess.run(["git", "-C", base_yaml_dir, "pull"], check=True)
    else:
        print(f"Cloning repository from {repo_url}...")
        subprocess.run(["git", "clone", repo_url, base_yaml_dir], check=True)
    
    # Remove existing log file if it exists.
    if os.path.exists(log_file):
        os.remove(log_file)
    # Remove existing output directory (optional)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Walk through all directories in base_yaml_dir to convert YAML to JSON.
    for root, dirs, files in os.walk(base_yaml_dir):
        for file in files:
            if file.endswith(".yaml"):
                yaml_path = os.path.join(root, file)
                # Create a similar relative structure under output_dir.
                rel_path = os.path.relpath(yaml_path, base_yaml_dir)
                json_path = os.path.join(output_dir, os.path.splitext(rel_path)[0] + ".json")
                loader = get_loader_for_file(yaml_path)
                convert_yaml_to_json(yaml_path, json_path, loader_cls=loader, log_file=log_file)
    
    # Delete the repository folder after conversion.
    if os.path.exists(base_yaml_dir):
        shutil.rmtree(base_yaml_dir)
        print(f"Deleted repository folder '{base_yaml_dir}'.")

if __name__ == "__main__":
    main()
