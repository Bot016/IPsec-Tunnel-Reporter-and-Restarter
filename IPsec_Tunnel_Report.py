import os
import json
import requests
import paramiko
import subprocess
import concurrent.futures



# NOTE: The path to the configuration file is set here at the end of the script.



# Load JSON configuration from file
def load_config(path):
    print(f"[INFO] Trying to read config file: {path}")
    try:
        with open(path, "r") as f:
            print(f"[INFO] Config file loaded successfully")
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config file '{path}': {e}")
        raise SystemExit(1)

# Validade Paths
def validate_paths(config):
    if not os.path.isfile(config["ssh_key_path"]):
        print(f"[ERROR] SSH key file not found: {config['ssh_key_path']}")
        raise SystemExit(1)
    else:
        print(f"[INFO] SSH key file found: {config['ssh_key_path']}")

    if not os.path.isfile(config["cert_path"]):
        print(f"[ERROR] Certificate file not found: {config['cert_path']}")
        raise SystemExit(1)
    else:
        print(f"[INFO] Certificate file found: {config['cert_path']}")

    output_dir = os.path.dirname(config["output_path"])
    if output_dir and not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"[INFO] Created output directory: {output_dir}")
        except Exception as e:
            print(f"[ERROR] Could not create output directory '{output_dir}': {e}")
            raise SystemExit(1)
    else:
        print(f"[INFO] Output directory exists: {output_dir}")
        
# Make a POST request to the API with authentication and SSL cert verification
def request_api_post(config, url, payload):
    api_key = config["api_key"]
    api_secret = config["api_secret"]
    cert_path = os.path.abspath(config["cert_path"])
    print(f"[INFO] Sending POST request to API: {url}")
    try:
        # Use the certificate file for SSL verification
        response = requests.post(url, json=payload, verify=cert_path, auth=(api_key, api_secret))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API communication error: {e}")
        raise SystemExit(1)

# Extract useful data from each tunnel child SA entry
def extract_child_data(entry):
    uuid = entry.get("uuid", "")
    description = entry.get("description", "")
    remote_ts = entry.get("remote_ts", "")

    # Parse company name and IP from description, expected format "Company - IP"
    if " - " in description:
        empresa, ip = [x.strip() for x in description.split(" - ", 1)]
    else:
        empresa, ip = description.strip(), ""

    # Extract the 3rd octet from the remote IP (used as tunnel ID)
    try:
        ip_parts = remote_ts.split("/")[0].split(".")
        id_octeto = ip_parts[2] if len(ip_parts) >= 3 else ""
    except Exception:
        id_octeto = ""

    return {
        "tunel": id_octeto,
        "empresa": empresa,
        "ip": ip,
        "uuid": uuid
    }

# Check if the remote IP responds to ping and return tunnel status info
def check_tunnel_status(tunel_data):
    print(f"[INFO] Pinging tunnel '{tunel_data['empresa']}' at IP {tunel_data['ip']}")
    status = "ON" if ping_host(tunel_data["ip"]) else "OFF"
    return {
        "tunel": int(tunel_data["tunel"]),
        "empresa": tunel_data["empresa"],
        "status": status,
        "uuid": tunel_data["uuid"]
    }

# Perform ping to the given IP address, return True if successful
def ping_host(ip):
    try:
        if os.name == 'nt':
            # Windows ping: 3 packeges
            cmd = ["ping", "-n", "3", "-w", "1000", ip]
        else:
            # Linux/macOS ping: 3 packeges
            cmd = ["ping", "-c", "3", "-W", "1", ip]

        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

# Write the result list (JSON) to the configured output file
def out_file(config, result_list):
    path = os.path.abspath(config["output_path"])
    with open(path, "w") as content:
        content.write(json.dumps(result_list, indent=4))
    print(f"[INFO] Report saved to: {path}")

# Connect via SSH and restart any tunnels that are offline by terminating child SA
def restart_tunnels(config, result_list):
    host = config["firewall_ip"]
    port = config["ssh_port"]
    user = config["ssh_user"]
    key_path = os.path.abspath(config["ssh_key_path"])
    print(f"[INFO] Connecting to firewall SSH at {config['firewall_ip']}:{config['ssh_port']}")

    # Load SSH private key (Ed25519)
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add unknown hosts
    client.connect(hostname=host, port=port, username=user, pkey=key)

    # Iterate tunnels and terminate the offline ones
    for tunnel in result_list:
        if tunnel["status"] == "OFF":
            print(f"[INFO] Restarting tunnel '{tunnel['empresa']}' (UUID: {tunnel['uuid']})")
            stdin, stdout, stderr = client.exec_command(f"swanctl --terminate --child {tunnel['uuid']}")
            stdout.channel.recv_exit_status()  # Wait for command to finish
    
    client.close()
    print("[INFO] SSH connection closed. Tunnel restart process completed.")

# Main program entry point
def main(path_config_file):
    config = load_config(path_config_file)
    validate_paths(config)
    
    # Prepare API payload with connection UUID from config
    connection_uuid = config["connection_uuid"]
    payload = {
        "current": 1,
        "rowCount": -1,
        "sort": {},
        "searchPhrase": "",
        "connection": connection_uuid 
    }

    # API URL - can be made configurable if needed
    url = f'https://{config["firewall_ip"]}:{config["web_port"]}/api/ipsec/connections/search_child'
    response = request_api_post(config, url, payload)
    print(f"[INFO] Received response from API with {len(response['rows'])} tunnels")

    # Extract and parse relevant data from API response
    children_parsed = [extract_child_data(r) for r in response["rows"]]

    # Sort tunnels by their numeric tunnel ID
    children_sorted = sorted(children_parsed, key=lambda x: int(x["tunel"]))

    # Check tunnel status concurrently for better performance
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result_list = list(executor.map(check_tunnel_status, children_sorted))
    
    # Output JSON report file
    out_file(config, result_list)
    
    # Restart offline tunnels via SSH
    restart_tunnels(config, result_list)

# You can modify the 'path_config_file' variable below to change the config file location.
if __name__ == "__main__":
    path_config_file = "config.json"
    main(path_config_file)
