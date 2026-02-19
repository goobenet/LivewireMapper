# Livewire Mapper v5.3.0
### The "Smart Conflict" Edition

Livewire Mapper is a specialized network auditing and audio monitoring tool designed for **Axia Livewire+** environments. It provides real-time visibility into source/destination routing, clock synchronization, and channel assignment conflicts without requiring a full routing protocol suite like Pathfinder.

---

## 🚀 Quick Start
1. **NIC IP**: Enter the IP address of the network card on your PC physically connected to the Livewire VLAN.
2. **Password**: Enter your standard Axia Node/Driver password (default is often blank or `node`).
3. **Start Scan**: Click to begin multicast discovery. The tool will automatically find every hardware node and software driver on your subnet.
4. **Export**: Use the **Export CSV** button at any time to save a full snapshot of your current network map.

---

## 🛠 Key Features

### 1. Smart Conflict Engine
* **Intelligent Filtering**: The system distinguishes between actual channel collisions and intentional backfeeds (sources starting with "To:").
* **Visual Alerts**: Real conflicts are highlighted in **Orange** in the source list.
* **Red Log Reporting**: Physical hardware collisions are logged in **Red** in the Log tab for immediate troubleshooting.

### 2. Audio Monitor & Recording
* **Live Monitoring**: Select any source and click **PLAY** to listen to the stream via the integrated VLC engine.
* **Disk Protection**: The recorder monitors available storage in real-time. It will automatically stop if space falls below 500MB to prevent system instability.
* **Timed Captures**: Set a recording limit (15–240 minutes) to take automated "air-check" snapshots of any channel.

### 3. Network Diagnostics
* **Network Master**: Automatically identifies which physical node is currently acting as the PTP/Clock Master.
* **Trace Node**: Click "Trace Node IP" to instantly filter the view to only show audio associated with a specific piece of hardware.

---

## 📋 Requirements
* **VLC Media Player**: Must be installed in `C:\Program Files\VideoLAN\VLC` for audio playback and recording.
* **Python Dependencies**: 
    * `python-vlc`
* **Network**: The host PC must have IGMP access to the Livewire VLAN to receive discovery packets on `239.192.255.3`.

---

## 📂 File Exports
CSV exports include the following data for every discovered source:
* **Channel Number**
* **Source Name**
* **Multicast IP**
* **Physical Node IP**
* **Device Type** (Hardware Node vs. Software Driver)
* **Sync Status** (Master vs. Slave)

---
*Developed for Broadcast Engineering & Network Maintenance.*
