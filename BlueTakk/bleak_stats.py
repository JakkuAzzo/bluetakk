import os
import json
import glob
import argparse
import asyncio
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import mplcursors
import numpy as np
from matplotlib.widgets import Button, Slider
from datetime import datetime

# Global page index and page list for interactive switching.
current_page = 0
pages = ["bar", "pie", "scatter", "recommendation"]

# Global variable to hold animation so it isn’t garbage collected.
_global_anim = None
_global_anim_basic = None  # global to hold the basic scan animation
_global_anim_detailed = None  # global to hold the detailed scan animation
_action_buttons = []       # Global container for action buttons
_bar_offset = 0  # Holds the slider value for bar chart offset

def draw_page(page, devices, ax, bar_offset=0, bar_display_count=10):
    ax.clear()
    if page == "bar":
        # Frequency (Bar) Chart: show frequency by device name.
        names = [d.get("name") or "Unknown" for d in devices]
        unique_names = sorted(list(set(names)))
        counts = [names.count(n) for n in unique_names]
        if len(unique_names) > bar_display_count:
            display_names = unique_names[bar_offset:bar_offset + bar_display_count]
            display_counts = [names.count(n) for n in display_names]
        else:
            display_names = unique_names
            display_counts = counts
        # Create bars and make each bar pickable.
        bars = ax.bar(display_names, display_counts, color="tab:blue")
        for bar in bars:
            bar.set_picker(True)
        ax.set_title("Device Frequency (Hover for details)")
        ax.set_ylabel("Frequency")
        ax.tick_params(axis="x", rotation=45)
        # Use mplcursors so annotation appears while hovering.
        cursor = mplcursors.cursor(bars, hover=True, highlight=True)
        @cursor.connect("add")
        def on_add(sel):
            i = sel.index
            # Find first matching device for this bar.
            device_detail = None
            for dev in devices:
                if (dev.get("name") or "Unknown") == display_names[i]:
                    device_detail = dev
                    break
            text = f"{display_names[i]}"
            if device_detail:
                text += f"\nAddress: {device_detail.get('address','N/A')}"
                text += f"\nRSSI: {device_detail.get('rssi','N/A')}"
            sel.annotation.set_text(text)
        # Connect a pick_event to handle double-clicks.
        def on_pick(event):
            if event.mouseevent.dblclick:
                artist = event.artist
                # Find the index of the picked bar.
                for i, bar in enumerate(bars):
                    if bar == artist:
                        idx = i
                        break
                else:
                    idx = 0
                # Find matching device.
                device_detail = None
                for dev in devices:
                    if (dev.get("name") or "Unknown") == display_names[idx]:
                        device_detail = dev
                        break
                if device_detail:
                    # Open a new detail window with full information.
                    from matplotlib import pyplot as plt
                    # Assumes open_detail_window() is defined.
                    open_detail_window(device_detail, f"Details for {display_names[idx]}")
        ax.figure.canvas.mpl_connect("pick_event", on_pick)
    elif page == "pie":
        companies = []
        for d in devices:
            manu = d.get("manufacturer_data")
            comp = "Unknown" if not manu else f"Company {list(manu.keys())[0]:04X}"
            companies.append(comp)
        if companies:
            unique_comps = list(set(companies))
            comp_counts = [companies.count(c) for c in unique_comps]
            pastel = plt.cm.get_cmap("Pastel1")
            ax.pie(
                comp_counts,
                labels=unique_comps,
                autopct='%1.1f%%',
                startangle=90,
                colors=pastel.colors,
            )
            ax.set_title("Devices by Company")
        else:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center")
            ax.set_title("Devices by Company")
    elif page == "scatter":
        scatter_x, scatter_y, labels = [], [], []
        for d in devices:
            rssi = d.get("rssi")
            distance = d.get("distance_m")
            if rssi is not None and distance is not None and not np.isnan(distance):
                angle = np.random.uniform(0, 2*np.pi)
                scatter_x.append(distance * np.cos(angle))
                scatter_y.append(distance * np.sin(angle))
                labels.append(d.get("name") or d.get("address") or "Unknown")
        if scatter_x and scatter_y:
            sc = ax.scatter(scatter_x, scatter_y, c=scatter_x, cmap="viridis",
                            s=100, edgecolor="black", alpha=0.8)
            ax.set_title("Estimated Distance Map")
            ax.set_xlabel("X (m)")
            ax.set_ylabel("Y (m)")
            cursor = mplcursors.cursor(sc, hover=True)
            @cursor.connect("add")
            def on_add_scatter(sel):
                i = sel.index
                sel.annotation.set_text(labels[i])
        else:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center")
            ax.set_title("Estimated Distance Map")
    elif page == "recommendation":
        rec = []
        for d in devices:
            if (d.get("rssi") is not None and d.get("distance_m") is not None 
                and d.get("tx_power") is not None):
                if d.get("rssi") > -70 and d.get("distance_m") < 5:
                    rec.append(d)
        if rec:
            rec_names = [d.get("name") or d.get("address") or "Unknown" for d in rec]
            bars = ax.bar(rec_names, [1]*len(rec), color="tab:orange")
            ax.set_title("Recommended Devices")
            ax.set_ylabel("Score")
            ax.tick_params(axis="x", rotation=45)
            cursor = mplcursors.cursor(bars, hover=True)
            @cursor.connect("add_rec")
            def on_add_rec(sel):
                i = sel.index
                detail = "\n".join([f"{k}: {v}" for k, v in rec[i].items()])
                sel.annotation.set_text(detail)
        else:
            ax.text(0.5, 0.5, "No Recommended Devices", ha="center", va="center")
            ax.set_title("Recommended Devices")

def open_detail_window(data, title):
    """
    Opens a new window with the given chart data and interactive buttons:
    Copy Data, Save JSON, Save PDF, and Run Vulnerability Scan.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.clear()
    # Display the provided data (assumed to be a dict or list)
    if isinstance(data, dict):
        text = json.dumps(data, indent=2)
    else:
        text = "\n".join(str(x) for x in data)
    ax.text(0.5, 0.5, text, ha="center", va="center", wrap=True)
    ax.set_title(title)
    ax.axis('off')
    
    # Create buttons for actions below the text.
    btn_copy = Button(plt.axes((0.1, 0.01, 0.15, 0.07)), "Copy Data")
    btn_save_json = Button(plt.axes((0.3, 0.01, 0.15, 0.07)), "Save JSON")
    btn_save_pdf = Button(plt.axes((0.5, 0.01, 0.15, 0.07)), "Save PDF")
    btn_run_vuln = Button(plt.axes((0.7, 0.01, 0.15, 0.07)), "Run Vuln Scan")
    
    def copy_callback(event):
        try:
            import pyperclip
            pyperclip.copy(text)
            print("Data copied to clipboard.")
        except Exception as e:
            print("Error copying data:", e)
    
    def save_json_callback(event):
        filename = f"{title.replace(' ', '_')}.json"
        with open(filename, "w") as f:
            f.write(text)
        print(f"Data saved to {filename}.")
    
    def save_pdf_callback(event):
        filename = f"{title.replace(' ', '_')}.pdf"
        fig.savefig(filename)
        print(f"Data saved to {filename}.")
    
    def run_vuln_callback(event):
        # For demonstration, simply print a message.
        print("Running vulnerability scan on selected device(s)...")
    
    btn_copy.on_clicked(copy_callback)
    btn_save_json.on_clicked(save_json_callback)
    btn_save_pdf.on_clicked(save_pdf_callback)
    btn_run_vuln.on_clicked(run_vuln_callback)
    
    show_and_limit_figures(fig)

def open_new_page_window(page, devices):
    """
    Opens a new static Matplotlib window showing the specified page using the current device data.
    """
    fig_new, ax_new = plt.subplots(figsize=(10, 6))
    manager = fig_new.canvas.manager
    if manager is not None:
        manager.set_window_title(f"Detailed View - {page}")
    # Draw the requested page once.
    draw_page(page, devices, ax_new)
    # (Optionally, for the "bar" page, attach a pick_event to allow double-clicks to open a detail window.)
    if page == "bar":
        # Example pick-event callback (modify as needed).
        def on_pick(event):
            if event.mouseevent.dblclick:
                # Identify the selected bar.
                artist = event.artist
                if hasattr(artist, "get_x"):
                    # For simplicity, assume the annotation in draw_page already displays a label.
                    sel_label = event.artist.get_x()  # not ideal – you might instead parse the text label.
                    # Find the matching device detail.
                    for dev in devices:
                        if (dev.get("name") or "Unknown") in str(sel_label):
                            open_detail_window(dev, f"Details for {dev.get('name', 'Unknown')}")
                            break
        fig_new.canvas.mpl_connect("pick_event", on_pick)
    show_and_limit_figures(fig_new)

def async_live_update_detailed_stats_data(live_data):
    """
    Opens a live-updating main window that shows the Frequency view (with a slider).
    The top buttons now open new static windows for each page.
    """
    global _global_anim_detailed, _bar_offset
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 8))
    manager = fig.canvas.manager
    if manager is not None:
        manager.set_window_title("Live Detailed Scan – Frequency View")
    
    # --- Create Page-Open Buttons (each opens a new window for its page) ---
    button_labels = ["Frequency", "Company", "Map", "Recommendation"]
    # Positions (in figure coordinates): adjust as needed.
    button_positions = (
        (0.1, 0.92, 0.15, 0.06),
        (0.3, 0.92, 0.15, 0.06),
        (0.5, 0.92, 0.15, 0.06),
        (0.7, 0.92, 0.15, 0.06)
    )
    # Instead of switching the main figure’s page, each button opens a new window.
    def make_new_window_callback(page):
        def callback(event):
            devices = live_data.get("devices", [])
            open_new_page_window(page, devices)
        return callback

    for i, label in enumerate(button_labels):
        btn_ax = fig.add_axes(button_positions[i])
        btn = Button(btn_ax, label, hovercolor="lightgreen")
        # pages list order: ["bar", "pie", "scatter", "recommendation"]
        btn.on_clicked(make_new_window_callback(["bar", "pie", "scatter", "recommendation"][i]))
    
    # --- Create a Slider for the main Frequency view ---
    # Initialize with default max=10 to avoid identical limit warnings.
    slider_ax = fig.add_axes((0.1, 0.05, 0.3, 0.03))
    slider_bar = Slider(ax=slider_ax, label="Bar Offset", valmin=0, valmax=10, valinit=0, valstep=1)
    def update_offset(val):
        global _bar_offset
        _bar_offset = int(val)
    slider_bar.on_changed(update_offset)
    
    def animate(frame):
        devices = live_data.get("devices", [])
        ax.clear()
        # Always draw the Frequency view in the live-updating main window.
        draw_page("bar", devices, ax, bar_offset=_bar_offset, bar_display_count=10)
        return ax,
    
    _global_anim_detailed = animation.FuncAnimation(fig, animate, interval=500, blit=False, save_count=50)
    plt.show(block=False)
    
    async def updater():
        while plt.fignum_exists(fig.number):
            plt.pause(0.1)
            await asyncio.sleep(0.1)
        print("Live detailed scan window closed.")
    return updater()

def async_live_update_stats_data(live_data):
    """
    Displays a basic live scan visualization: one figure with two subplots.
    - Left subplot: a bar chart for the total number of persisted devices.
    - Right subplot: a table of persistent device data (Name, Address, RSSI) for a fixed number of rows.
      A slider allows scrolling through all devices.
    Next to each displayed row in the table three buttons are added:
      “Vuln” (to run vulnerability scan), “Copy Name”, “Copy Addr”.
    When the figure is closed, the persistent device dictionary is saved to a JSON file in the sessions folder.
    """
    plt.ion()  # Enable interactive mode.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    manager = fig.canvas.manager
    if manager is not None:
        manager.set_window_title("Live Scan Visualization")

    # Create a slider widget for scrolling through table rows.
    slider_ax = fig.add_axes((0.70, 0.05, 0.25, 0.03))  # below the right subplot 
    slider = Slider(
        ax=slider_ax,
        label='Row Offset',
        valmin=0,
        valmax=0,
        valinit=0,
        valstep=1,
    )
    
    display_rows = 10  # Number of table rows to display at once.

    def animate(frame):
        global _action_buttons
        # Left subplot: update bar chart.
        count = live_data.get("devices_found", 0)
        ax1.clear()
        ax1.bar(["Captured Devices"], [count], color="blue", label="Count")
        ax1.set_ylim(0, max(10, count+1))
        ax1.set_title(f"Live Captured Devices: {count}")
        ax1.legend()
        
        # Right subplot: update device table.
        ax2.clear()
        devices_dict = live_data.get("devices", {})
        all_devices = list(devices_dict.values())
        
        # Update slider maximum value based on total devices.
        max_offset = max(0, len(all_devices) - display_rows)
        slider.ax.clear()
        slider.__init__(slider.ax, 'Row Offset', 0, max_offset, valinit=slider.val, valstep=1)
        
        offset = int(slider.val)
        rows_to_display = all_devices[offset:offset+display_rows]
        if rows_to_display:
            table_rows = []
            for dev in rows_to_display:
                name = dev.get("name") or "N/A"
                addr = dev.get("address") or "N/A"
                rssi = dev.get("rssi")
                table_rows.append([name, addr, str(rssi)])
            ax2.axis("tight")
            ax2.axis("off")
            tbl = ax2.table(cellText=table_rows,
                            colLabels=["Name", "Address", "RSSI (dBm)"],
                            cellLoc="center",
                            loc="center")
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8)
            tbl.scale(1, 1.2)
        else:
            ax2.text(0.5, 0.5, "No devices found", ha="center", va="center")
        
        # Remove any existing action buttons.
        for btn in _action_buttons:
            btn.ax.remove()
        _action_buttons = []
        
        # Add buttons for each displayed row.
        if rows_to_display:
            # Get right subplot position in figure coordinates.
            bbox = ax2.get_position()
            cell_height = bbox.height / display_rows
            btn_width = 0.04
            btn_height = cell_height * 0.8
            x_offset = 0.01  # gap after ax2's right edge
            for i, dev in enumerate(rows_to_display):
                # Calculate button vertical position.
                y = bbox.y1 - (i+1)*cell_height + (cell_height - btn_height) / 2
                # Define positions for three buttons.
                pos1 = (bbox.x1 + x_offset, y, btn_width, btn_height)
                pos2 = (bbox.x1 + x_offset + btn_width + 0.005, y, btn_width, btn_height)
                pos3 = (bbox.x1 + x_offset + 2*(btn_width + 0.005), y, btn_width, btn_height)
                btn1 = Button(plt.axes(pos1), "Vuln", color='lightgray', hovercolor='yellow')
                btn2 = Button(plt.axes(pos2), "Copy Name", color='lightgray', hovercolor='yellow')
                btn3 = Button(plt.axes(pos3), "Copy Addr", color='lightgray', hovercolor='yellow')
                
                # Create callbacks that capture the current device.
                def make_vuln_callback(dev):
                    def vuln_callback(event):
                        print(f"Running vulnerability scan on {dev.get('address')}")
                        # Here, insert vulnerability scanning logic for dev.
                    return vuln_callback
                def make_copy_name_callback(dev):
                    def copy_name_callback(event):
                        try:
                            import pyperclip
                            pyperclip.copy(dev.get("name", ""))
                            print(f"Copied name: {dev.get('name')}")
                        except Exception as e:
                            print(e)
                    return copy_name_callback
                def make_copy_addr_callback(dev):
                    def copy_addr_callback(event):
                        try:
                            import pyperclip
                            pyperclip.copy(dev.get("address", ""))
                            print(f"Copied address: {dev.get('address')}")
                        except Exception as e:
                            print(e)
                    return copy_addr_callback
                
                btn1.on_clicked(make_vuln_callback(dev))
                btn2.on_clicked(make_copy_name_callback(dev))
                btn3.on_clicked(make_copy_addr_callback(dev))
                
                _action_buttons.extend([btn1, btn2, btn3])
        
        return (ax1, ax2)
    
    global _global_anim_basic
    _global_anim_basic = animation.FuncAnimation(fig, animate, interval=500, blit=False, save_count=50)
    plt.show(block=False)
    
    async def updater():
        while plt.fignum_exists(fig.number):
            plt.pause(0.1)
            await asyncio.sleep(0.1)
        print("Basic live visualization window closed.")
        # When closed, save the persistent devices to a JSON file.
        session_data = {"devices": live_data.get("devices", {})}
        sessions_dir = "sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        filename = os.path.join(
            sessions_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w") as f:
            json.dump(session_data, f, indent=4)
        print(f"Session details saved to {filename}")
    
    return updater()

def show_stats(data):
    print("\nSession Statistics:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    chart_labels = []
    chart_values = []
    for key in ["connection_time_sec", "data_transferred_kb", "signal_strength"]:
        if key in data:
            chart_labels.append(key)
            chart_values.append(data[key])
    plt.figure()
    plt.bar(chart_labels, chart_values, color='green')
    plt.xlabel("Metric")
    plt.ylabel("Value")
    title = "Bluetooth Session Statistics"
    if data.get("device_name") and data.get("device_address"):
        title += f"\nDevice: {data['device_name']} ({data['device_address']})"
    plt.title(title)
    plt.savefig("session_stats.png")
    print("\nSession statistics diagram saved as 'session_stats.png'.")
    plt.show()

def live_update_stats_file(live_file):
    fig, ax = plt.subplots()
    while True:
        if os.path.exists(live_file):
            with open(live_file, "r") as f:
                try:
                    data = json.load(f)
                except json.decoder.JSONDecodeError:
                    data = {}
        else:
            data = {}
        device_count = len(data)
        ax.clear()
        ax.bar(["Captured Devices"], [device_count], color='blue')
        ax.set_ylim(0, max(10, device_count + 1))
        ax.set_title(f"Live Captured Devices: {device_count}")
        plt.draw()
        plt.pause(0.5)

def load_latest_session(device_address=""):
    sessions_dir = "sessions"
    session_files = glob.glob(os.path.join(sessions_dir, "session_*.json"))
    if device_address:
        session_files = [f for f in session_files if device_address in f]
    if not session_files:
        print("No session files found.")
        return None
    session_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = session_files[0]
    with open(latest_file, "r") as f:
        session_data = json.load(f)
    return session_data.get("current_session_details")

def show_and_limit_figures(fig):
    plt.show()
    # Close all but the last two figures
    figs = list(map(plt.figure, plt.get_fignums()))
    while len(figs) > 2:
        f = figs.pop(0)
        plt.close(f)

def main():
    parser = argparse.ArgumentParser(description="Bluetooth Session Stats")
    parser.add_argument("--device_address", type=str, default="",
                        help="Connected device address")
    parser.add_argument("--live", action="store_true",
                        help="Enable live updating visualization (from file)")
    args = parser.parse_args()
    if args.live:
        live_update_stats_file("filtered_scan_results.json")
    else:
        session_details = load_latest_session(device_address=args.device_address)
        if not session_details:
            print("No session details available.")
            return
        connection_stats = session_details.get("connection_stats", {})
        connection_stats["device_address"] = session_details.get("device_address", args.device_address)
        connection_stats["device_name"] = session_details.get("device_name", "")
        show_stats(connection_stats)

if __name__ == "__main__":
    main()
