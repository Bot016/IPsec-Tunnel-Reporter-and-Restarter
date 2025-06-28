import json
import requests
import subprocess
import concurrent.futures
import paramiko

# Load JSON configuration from file
def load_config(path):
    with open(path, "r") as f:
        return json.load(f)

# Make a POST request to the API with authentication and SSL cert verification
def request_api_post(config, url, payload):
    api_key = config["api_key"]
    api_secret = config["api_secret"]
    cert_path = config["cert_path"]
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
        # Windows ping: send 3 packets, 1000ms timeout each
        result = subprocess.run(
            ["ping", "-n", "3", "-w", "1000", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False

# Write the result list (JSON) to the configured output file
def out_file(config, result_list):
    path = config["output_path"]
    with open(path, "w") as content:
        content.write(json.dumps(result_list, indent=4))

# Connect via SSH and restart any tunnels that are offline by terminating child SA
def restart_tunnels(config, result_list):
    host = config["firewall_ip"]
    port = config["ssh_port"]
    user = config["ssh_user"]
    key_path = config["ssh_key_path"]

    # Load SSH private key (Ed25519)
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add unknown hosts
    client.connect(hostname=host, port=port, username=user, pkey=key)

    # Iterate tunnels and terminate the offline ones
    for tunnel in result_list:
        if tunnel["status"] == "OFF":
            stdin, stdout, stderr = client.exec_command(f"swanctl --terminate --child {tunnel['uuid']}")
            stdout.channel.recv_exit_status()  # Wait for command to finish

    client.close()

# Main program entry point
def main(path_config_file):
    config = load_config(path_config_file)
    
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
    print(url)
    response = request_api_post(config, url, payload)

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


if __name__ == "__main__":
    path_config_file = ".\config.json"  # Path to config file
    main(path_config_file)
