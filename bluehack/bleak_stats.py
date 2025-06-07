import os
import json
import glob
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# --- Helper: Estimate distance from RSSI (a simple approximation) ---
def estimate_distance(rssi, tx_power=-59, n=2):
    """
    Estimates distance (in meters) given RSSI.
    tx_power: assumed measured power at 1 meter (in dBm)
    n: signal propagation constant
    """
    try:
        distance = 10 ** ((tx_power - rssi) / (10 * n))
        return round(distance, 2)
    except Exception:
        return "N/A"

# --- Helper: Display device details in a new figure as a table ---
def display_device_details(device_name, devices):
    # Filter devices from the list that match the given device_name.
    filtered = [d for d in devices if (d.get("name") or "Unknown") == device_name]
    if not filtered:
        print(f"No details found for device {device_name}")
        return

    # Prepare table data. Columns: Name, Address, RSSI, Estimated Distance, and Details.
    headers = ["Name", "Address", "RSSI", "Estimated Distance (m)", "Details"]
    table_data = []
    for device in filtered:
        name = device.get("name") or "Unknown"
        address = device.get("address", "N/A")
        rssi = device.get("rssi", "N/A")
        distance = estimate_distance(rssi) if isinstance(rssi, (int, float)) else "N/A"
        # Create a summary of details if available.
        details = device.get("details", [])
        if details:
            svc_details = []
            for svc in details:
                svc_name = svc.get("name", "Unknown")
                svc_uuid = svc.get("uuid", "N/A")
                svc_handle = svc.get("handle", "N/A")
                # If there are characteristics, join them with a comma.
                chars = svc.get("characteristics", [])
                if chars:
                    char_summary = ", ".join(chars)
                    svc_details.append(f"{svc_name} (UUID: {svc_uuid}, Handle: {svc_handle}, Chars: {char_summary})")
                else:
                    svc_details.append(f"{svc_name} (UUID: {svc_uuid}, Handle: {svc_handle})")
            detail_str = "\n".join(svc_details)
        else:
            detail_str = "No details"
        table_data.append([name, address, rssi, distance, detail_str])
    
    # Create a new figure for the table with increased size.
    fig, ax = plt.subplots(figsize=(max(8, len(headers)*2), len(table_data)*1.2 + 1))
    ax.axis("tight")
    ax.axis("off")
    the_table = ax.table(cellText=table_data, colLabels=headers, loc="center")
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(14)  # Increase the font size here.
    
    # Optionally adjust cell heights if needed.
    for key, cell in the_table.get_celld().items():
        cell.set_height(0.1)

    ax.set_title(f"Details for Device: {device_name}", fontweight="bold", fontsize=16)
    plt.show()

# --- Helper: Display a bar chart for a specific scan file ---
def display_scan_bar_chart_from_file(scan_file):
    with open(scan_file, "r") as f:
        data = json.load(f)
    if not data:
        print("Scan file is empty.")
        return

    device_names = [d.get("name") or "Unknown" for d in data]
    # Count the occurrences by device name.
    unique_names = sorted(list(set(device_names)))
    counts = [device_names.count(n) for n in unique_names]

    fig, ax = plt.subplots()
    bars = ax.bar(unique_names, counts, color="blue", picker=True)
    ax.set_xlabel("Device Name")
    ax.set_ylabel("Count")
    ax.set_title(f"Stats for Scan:\n{os.path.basename(scan_file)}")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Create mapping from bar to device name.
    bar_mapping = {}
    for idx, bar in enumerate(bars):
        bar_mapping[bar] = unique_names[idx]

    # Callback when a bar is clicked.
    def on_bar_pick(event):
        bar = event.artist
        dev_name = bar_mapping.get(bar)
        if dev_name:
            print(f"Clicked on device: {dev_name}")
            # Display new table window showing all details for this device from the scan data.
            display_device_details(dev_name, data)

    fig.canvas.mpl_connect("pick_event", on_bar_pick)
    plt.show()

def show_stats_last_scan():
    """
    Load the most recent scan file from the recent_scan folder,
    then display an interactive bar chart where clicking a bar shows a detailed table.
    """
    recent_folder = os.path.join(os.getcwd(), "recent_scan")
    scan_files = glob.glob(os.path.join(recent_folder, "bleak_discover_*.json"))
    if not scan_files:
        print("No recent scan files found.")
        return
    # Sort files by modification time descending.
    scan_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = scan_files[0]
    with open(latest_file, "r") as f:
        data = json.load(f)
    if not data:
        print("Latest scan file is empty.")
        return

    device_names = [d.get("name") or "Unknown" for d in data]
    unique_names = sorted(list(set(device_names)))
    counts = [device_names.count(n) for n in unique_names]

    fig, ax = plt.subplots()
    bars = ax.bar(unique_names, counts, color="blue", picker=True)
    ax.set_xlabel("Device Name")
    ax.set_ylabel("Count")
    ax.set_title(f"Stats for Last Scan:\n{os.path.basename(latest_file)}")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Map each bar to its corresponding device name.
    bar_mapping = {}
    for idx, bar in enumerate(bars):
        bar_mapping[bar] = unique_names[idx]

    # When a bar is clicked, open a new window with a table of details.
    def on_bar_pick(event):
        bar = event.artist
        dev_name = bar_mapping.get(bar)
        if dev_name:
            print(f"Clicked on device: {dev_name}")
            display_device_details(dev_name, data)

    fig.canvas.mpl_connect("pick_event", on_bar_pick)
    plt.show()

def show_stats_all_scans():
    """
    Loads all scan files from the recent_scan folder and plots the number
    of devices found per scan. Clicking on a dot corresponding to a scan file
    opens the bar chart for that scan (similar to show_stats_last_scan).
    """
    recent_folder = os.path.join(os.getcwd(), "recent_scan")
    scan_files = glob.glob(os.path.join(recent_folder, "bleak_discover_*.json"))
    if not scan_files:
        print("No recent scan files found.")
        return
    # Sort files by modification time ascending.
    scan_files.sort(key=os.path.getmtime)
    timestamps = []
    counts = []
    for file in scan_files:
        with open(file, "r") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Error loading {file}: {e}")
                continue
        count = len(data) if isinstance(data, list) else 0
        # Extract timestamp from filename, expected format: bleak_discover_YYYYMMDD_HHMMSS.json
        basename = os.path.basename(file)
        ts = basename.replace("bleak_discover_", "").replace(".json", "")
        timestamps.append(ts)
        counts.append(count)

    fig, ax = plt.subplots()
    # Plot dots with picking enabled.
    line = ax.plot(timestamps, counts, marker="o", linestyle="-", picker=5)[0]
    ax.set_xlabel("Scan Timestamp")
    ax.set_ylabel("Number of Devices Found")
    ax.set_title("Stats for All Scans")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Callback: when a dot is clicked, identify which scan and display its bar chart.
    def on_dot_pick(event):
        ind = event.ind[0]
        scan_file = scan_files[ind]
        print(f"Clicked on scan file: {os.path.basename(scan_file)}")
        # Display the bar chart for this scan file.
        display_scan_bar_chart_from_file(scan_file)

    fig.canvas.mpl_connect("pick_event", on_dot_pick)
    plt.show()

def menu():
    """
    Provides a menu:
       1. Show stats for last scan (recent_scan folder)
       2. Show stats for all scans (recent_scan folder)
       3. Exit
    """
    while True:
        print("\n=== Bleak Stats Menu ===")
        print("1. Show stats for last scan")
        print("2. Show stats for all scans")
        print("3. Exit")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            show_stats_last_scan()
        elif choice == "2":
            show_stats_all_scans()
        elif choice == "3":
            print("Exiting Bleak Stats.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    menu()