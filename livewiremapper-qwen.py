import os
import socket
import struct
import threading
import re
import random
import shutil
import csv
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

# --- VLC CONFIGURATION ---
VLC_DIR = r"C:\Program Files\VideoLAN\VLC"
if os.path.isdir(VLC_DIR):
    # Ensure DLL directory is added for Python 3.8+ compatibility
    try:
        os.add_dll_directory(VLC_DIR)
    except AttributeError:
        pass

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

class LivewireGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Livewire Mapper (v5.3.0) [Audio Fix]") # Updated Title
        self.root.geometry("1650x1000")
        self.root.configure(bg="#2b2b2b")
        
        self.master_table = {} 
        self.dest_table = []    
        self.scanned_ips = set()
        self.running = False
        self.is_recording = False
        self.recording_start_time = None
        self.save_directory = None
        self.network_master_ip = "Searching..." 
        self.trace_node_ip = None
        
        self.player = None
        if VLC_AVAILABLE:
            try:
                # FIX 1: Added --audio-output-module=directsound for Windows reliability
                # Removed --quiet to allow error messages in console/log if audio fails
                instance_args = "--no-video --network-caching=300 --audio-output-module=directsound"
                self.instance = vlc.Instance(instance_args)
                self.player = self.instance.media_player_new()
            except Exception as e: 
                messagebox.showerror("VLC Error", f"Failed to initialize VLC Player: {e}")

        self.meter_running = False
        self.setup_ui()
        self.update_disk_space()

    def setup_ui(self):
        # Top Panel
        top_panel = tk.Frame(self.root, bg="#2b2b2b", pady=10)
        top_panel.pack(side=tk.TOP, fill=tk.X)
        
        conn_frame = tk.Frame(top_panel, bg="#2b2b2b")
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(conn_frame, text="NIC IP:", bg="#2b2b2b", fg="#cccccc").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(conn_frame, width=15); self.ip_entry.insert(0, ""); self.ip_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(conn_frame, text="Password:", bg="#2b2b2b", fg="#cccccc").pack(side=tk.LEFT, padx=5)
        self.pw_entry = tk.Entry(conn_frame, width=15, show="*"); self.pw_entry.pack(side=tk.LEFT, padx=5)
        self.btn_start = tk.Button(conn_frame, text="Start Scan", command=self.toggle_scan, bg="#28a745", fg="white", font=("Arial", 9, "bold"), width=12)
        self.btn_start.pack(side=tk.LEFT, padx=10)
        tk.Button(conn_frame, text="Export CSV", command=self.export_to_csv, bg="#6c757d", fg="white", width=12).pack(side=tk.LEFT, padx=2)

        # Network Master Label (Fixed)
        self.master_display = tk.Label(conn_frame, text=f"Network Master: {self.network_master_ip}", font=("Arial", 10, "bold"), fg="#4da6ff", bg="#2b2b2b")
        self.master_display.pack(side=tk.LEFT, padx=20)

        search_frame = tk.Frame(top_panel, bg="#2b2b2b")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", lambda *args: self.apply_filter())
        tk.Entry(search_frame, textvariable=self.search_var, width=35, bg="#3c3c3c", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Trace Node IP", command=self.do_node_trace, bg="#005a9e", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Clear Filters", command=self.reset_filters, bg="#444444", fg="white").pack(side=tk.LEFT, padx=2)

        self.status_bar = tk.Label(self.root, text="Nodes: 0 | Sources: 0 | Destinations: 0 | Conflicts: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#2b2b2b", fg="#888888", font=("Arial", 10))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.notebook = ttk.Notebook(self.root); self.notebook.pack(fill=tk.BOTH, expand=True, padx=10)
        self.map_frame = tk.Frame(self.notebook, bg="#1e1e1e"); self.dst_frame = tk.Frame(self.notebook, bg="#1e1e1e"); self.log_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.map_frame, text=" Sources "); self.notebook.add(self.dst_frame, text=" Destinations "); self.notebook.add(self.log_frame, text=" Log ")

        self.src_cols = ("ch", "name", "mcast", "ip", "type", "sync")
        self.tree = ttk.Treeview(self.map_frame, columns=self.src_cols, show="headings")
        self.tree.tag_configure('conflict', background='#804000', foreground='white')
        self.tree.tag_configure('backfeed', foreground='#4682B4', font=("Arial", 9, "bold"))
        for c in self.src_cols: self.tree.heading(c, text=c.upper(), command=lambda _c=c: self.sort_treeview(self.tree, _c, False))
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.dst_tree = ttk.Treeview(self.dst_frame, columns=("name", "out", "src", "ip"), show="headings")
        for c in ("name", "out", "src", "ip"): self.dst_tree.heading(c, text=c.upper(), command=lambda _c=c: self.sort_treeview(self.dst_tree, _c, False))
        self.dst_tree.pack(fill=tk.BOTH, expand=True)

        self.log_list = tk.Listbox(self.log_frame, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10)); self.log_list.pack(fill=tk.BOTH, expand=True)

        # Audio Monitor & Capture
        self.audio_frame = tk.LabelFrame(self.root, text=" Audio Capture & Control ", bg="#1e1e1e", fg="#00ff00", pady=10)
        self.audio_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.meter_canvas = tk.Canvas(self.audio_frame, width=200, height=120, bg="black", highlightthickness=0); self.meter_canvas.pack(side=tk.LEFT, padx=20)
        self.l_meter = self.meter_canvas.create_rectangle(40, 110, 80, 110, fill="#00ff00"); self.r_meter = self.meter_canvas.create_rectangle(120, 110, 160, 110, fill="#00ff00")
        ctrl_frame = tk.Frame(self.audio_frame, bg="#1e1e1e"); ctrl_frame.pack(side=tk.LEFT, padx=10)
        
        # FIX 2: Updated Status Label to indicate Audio State
        self.monitor_lbl = tk.Label(ctrl_frame, text="AUDIO OFF", bg="#1e1e1e", fg="#888888", font=("Consolas", 11)); self.monitor_lbl.pack(pady=2)
        
        timer_box = tk.Frame(ctrl_frame, bg="#1e1e1e"); timer_box.pack(pady=2)
        self.timer_lbl = tk.Label(timer_box, text="00:00", bg="#1e1e1e", fg="#555555", font=("Consolas", 10)); self.timer_lbl.pack(side=tk.LEFT)
        self.limit_var = tk.StringVar(value="60"); self.limit_menu = ttk.Combobox(timer_box, textvariable=self.limit_var, values=["15", "30", "60", "120", "240"], width=5, state="readonly"); self.limit_menu.pack(side=tk.LEFT, padx=5)
        self.path_lbl = tk.Label(ctrl_frame, text="Path: Default", bg="#1e1e1e", fg="#666666", font=("Arial", 8)); self.path_lbl.pack()
        self.disk_lbl = tk.Label(ctrl_frame, text="Disk: Checking...", bg="#1e1e1e", fg="#888888", font=("Arial", 9)); self.disk_lbl.pack()
        
        btn_box = tk.Frame(ctrl_frame, bg="#1e1e1e"); btn_box.pack(pady=5)
        tk.Button(btn_box, text="▶ PLAY", command=self.play_audio, bg="#28a745", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        self.btn_record = tk.Button(btn_box, text="● RECORD", command=self.toggle_record, bg="#444444", fg="white", width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_box, text="📁 PATH", command=self.set_save_path, bg="#666666", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_box, text="■ STOP", command=self.stop_all, bg="#dc3545", fg="white", width=8).pack(side=tk.LEFT, padx=2)

    # --- UPDATED FILTER & CONFLICT LOGIC ---
    def apply_filter(self):
        query = self.search_var.get().lower()
        for i in self.tree.get_children(): self.tree.delete(i)
        
        real_conflict_count = 0
        for ch, entries in sorted(self.master_table.items()):
            primary_sources = [e for e in entries if not e['name'].startswith("To:")]
            unique_primary_ips = set(e['ip'] for e in primary_sources)
            is_real_conflict = len(unique_primary_ips) > 1
            
            if is_real_conflict: 
                real_conflict_count += 1
                # Restore Red Log Reporting
                self.log_message(f"CONFLICT: Multiple sources on CH {ch} ({', '.join(unique_primary_ips)})", "red")
            
            for e in entries:
                if (not self.trace_node_ip or e['ip'] == self.trace_node_ip) and (not query or query in e['name'].lower() or query in str(ch)):
                    is_bf = e['name'].startswith("To:")
                    tags = ('conflict',) if is_real_conflict and not is_bf else ('backfeed',) if is_bf else ()
                    self.tree.insert("", "end", values=(ch, e['name'], e['mcast'], e['ip'], e['type'], e['sync']), tags=tags)
        
        for i in self.dst_tree.get_children(): self.dst_tree.delete(i)
        for d in self.dest_table:
            if (not self.trace_node_ip or d[0] == self.trace_node_ip) and (not query or query in d[2].lower()):
                src_info = self.master_table.get(d[3])
                src_txt = f"{d[3]} - {src_info[0]['name']}" if src_info else str(d[3])
                self.dst_tree.insert("", "end", values=(d[2], d[1], src_txt, d[0]))
        
        self.status_bar.config(text=f"Nodes: {len(self.scanned_ips)} | Sources: {len(self.master_table)} | Destinations: {len(self.dest_table)} | Conflicts: {real_conflict_count}")
        # Explicitly force master update
        self.master_display.config(text=f"Network Master: {self.network_master_ip}")

    # --- CORE LOGIC: DISCOVERY ---
    def toggle_scan(self):
        self.running = not self.running
        self.btn_start.config(text="STOP SCAN" if self.running else "START SCAN", bg="#dc3545" if self.running else "#28a745")
        if self.running: 
            self.log_message("Discovery started...")
            threading.Thread(target=self.discovery_loop, daemon=True).start()

    def discovery_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sock.bind(('0.0.0.0', 4001))
        try:
            mreq = struct.pack('4s4s', socket.inet_aton('239.192.255.3'), socket.inet_aton(self.ip_entry.get()))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except: self.log_message("Error: Invalid NIC IP for Multicast.", "red"); return

        while self.running:
            try:
                sock.settimeout(2); data, addr = sock.recvfrom(1024)
                if addr[0] not in self.scanned_ips:
                    self.scanned_ips.add(addr[0])
                    threading.Thread(target=self.get_node_full_info, args=(addr[0], self.pw_entry.get()), daemon=True).start()
            except: continue

    def get_node_full_info(self, ip, pw):
        try:
            with socket.create_connection((ip, 93), timeout=3) as s:
                s.sendall(f"LOGIN {pw}\r\nSRC\r\nDST\r\nFPSTAT\r\n".encode())
                import time; time.sleep(1.2); data = s.recv(65535).decode(errors='ignore')
                
                dtype = "Driver" if "lwwd" in data.lower() else "Node"
                mm = re.search(r'FPSTAT MASTER:(\d+)', data)
                if mm and int(mm.group(1)) > 0: 
                    self.network_master_ip = ip # Master found

                for nm, mc in re.findall(r'SRC\s+\d+\s+PSNM:"([^"]+)"\s+.*?RTPA:"([^"]+)"', data):
                    if mc != "0.0.0.0":
                        p = mc.split('.'); c = (int(p[2])*256)+int(p[3])
                        if c not in self.master_table: self.master_table[c] = []
                        if not any(e['ip'] == ip for e in self.master_table[c]):
                            self.master_table[c].append({'name': nm, 'ip': ip, 'type': dtype, 'sync': "MASTER" if ip == self.network_master_ip else "N/A", 'mcast': mc})
                
                for num, nm, addr in re.findall(r'DST\s+(\d+)\s+NAME:"([^"]*)"\s+.*?ADDR:"([^"]*)"', data):
                    sc = 0
                    if addr and addr != "0.0.0.0":
                        ipts = re.findall(r'\d+', addr)[:4]; sc = (int(ipts[2])*256)+int(ipts[3])
                    self.dest_table.append([ip, num, nm if nm else f"Out {num}", sc])
                
                self.root.after(0, self.apply_filter)
        except Exception as e: self.log_message(f"Node {ip} error: {e}", "red")

    # --- CSV & LOGGING ---
    def log_message(self, msg, color="#d4d4d4"): 
        self.log_list.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        self.log_list.itemconfig("end", fg=color); self.log_list.see("end")

    def export_to_csv(self):
        if not self.master_table: return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"Livewire_Map_{timestamp}.csv")
        if filepath:
            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["CHANNEL", "NAME", "MULTICAST IP", "NODE IP", "TYPE", "SYNC"])
                    for ch, entries in sorted(self.master_table.items()):
                        for e in entries:
                            writer.writerow([ch, e['name'], e['mcast'], e['ip'], e['type'], e['sync']])
                self.log_message(f"Exported to {os.path.basename(filepath)}")
            except Exception as e: self.log_message(f"Export Error: {e}", "red")

    # --- AUDIO & UTILS ---
    def set_save_path(self):
        path = filedialog.askdirectory()
        if path: self.save_directory = path; self.path_lbl.config(text=f"Path: ...{path[-25:]}"); self.update_disk_space()

    def update_disk_space(self):
        p = self.save_directory if self.save_directory else "."
        try:
            _, _, free = shutil.disk_usage(p)
            gb = free/(2**30)
            self.disk_lbl.config(text=f"Free: {gb:.1f} GB (~{gb/0.635:.1f} hrs)", fg="#00ff00" if gb > 5 else "red")
        except: pass
        self.root.after(30000, self.update_disk_space)

    def play_audio(self):
        sel = self.tree.selection()
        if not sel or not self.player: 
            return
        
        ch = int(self.tree.item(sel[0])['values'][0])
        
        # FIX 2: Explicitly set volume to maximum (100 is standard, max in VLC API is usually 128)
        self.player.audio_set_volume(100) 
        
        media_url = f"rtp://@{self.get_multicast_ip(ch)}:5004"
        self.player.set_media(self.instance.media_new(media_url))
        
        # Reset Player State to ensure fresh play
        self.player.stop() 
        self.player.play()
        
        self.meter_running = True
        self.monitor_lbl.config(text="PLAYING", fg="#00ff00")
        self.draw_meters()

    def draw_meters(self):
        # NOTE: These meters use random numbers and do not reflect actual audio levels.
        if not self.meter_running: return
        l, r = random.randint(45, 95), random.randint(45, 95)
        self.meter_canvas.coords(self.l_meter, 40, 110-l, 80, 110); self.meter_canvas.coords(self.r_meter, 120, 110-r, 160, 110)
        self.root.after(50, self.draw_meters)

    def toggle_record(self):
        if self.is_recording: 
            self.stop_recording()
            return
        
        sel = self.tree.selection()
        if not sel: 
            return
            
        v = self.tree.item(sel[0])['values']
        ch, name = v[0], re.sub(r'[^\w]', '', str(v[1]))
        fname = f"CH{ch}_{name}_{datetime.now().strftime('%H%M')}.wav"
        path = os.path.join(self.save_directory, fname) if self.save_directory else filedialog.asksaveasfilename(initialfile=fname)
        
        if path: 
            self.start_recording(ch, path)

    def start_recording(self, ch, path):
        # Create a new instance for recording to avoid conflicts with playback
        try:
            self.rec_instance = vlc.Instance("--no-video --quiet")
            self.rec_player = self.rec_instance.media_player_new()
            sout = f"#transcode{{acodec=s16l,channels=2,samplerate=48000}}:std{{access=file,mux=wav,dst='{path.replace("'", "''")}'}}"
            media_url = f"rtp://@{self.get_multicast_ip(ch)}:5004"
            
            self.rec_player.set_media(self.rec_instance.media_new(media_url, f":sout={sout}"))
            # Ensure volume is high for recording too
            self.rec_player.audio_set_volume(128) 
            
            self.rec_player.play()
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.btn_record.config(bg="red", text="■ STOP REC")
            self.monitor_lbl.config(text="RECORDING", fg="#ff0000")
            self.update_timer()
        except Exception as e:
            self.log_message(f"Recording Error: {e}", "red")

    def stop_recording(self):
        if hasattr(self, 'rec_player'): 
            self.rec_player.stop()
        
        self.is_recording = False
        self.btn_record.config(bg="#444444", text="● RECORD")
        self.timer_lbl.config(text="00:00")
        self.monitor_lbl.config(text="READY", fg="#888888")

    def update_timer(self):
        if not self.is_recording: return
        elapsed = (datetime.now() - self.recording_start_time).seconds
        if elapsed >= int(self.limit_var.get()) * 60: 
            self.stop_recording(); return
        
        self.timer_lbl.config(text=f"{elapsed//60:02d}:{elapsed%60:02d} / {int(self.limit_var.get()):02d}:00")
        self.root.after(1000, self.update_timer)

    def stop_all(self):
        if self.player: 
            self.player.stop()
        
        self.meter_running = False
        self.monitor_lbl.config(text="READY", fg="#888888")
        
        if self.is_recording: 
            self.stop_recording()

    def get_multicast_ip(self, ch): return f"239.192.{ch // 256}.{ch % 256}"
    
    def sort_treeview(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): 
            tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))
        
    def do_node_trace(self):
        s = self.tree.selection() or self.dst_tree.selection()
        if s: 
            self.trace_node_ip = self.tree.item(s[0])['values'][3] if self.tree.selection() else self.dst_tree.item(s[0])['values'][3]
            self.apply_filter()
            
    def reset_filters(self): 
        self.trace_node_ip = None; self.search_var.set(""); self.apply_filter()

if __name__ == "__main__":
    root = tk.Tk(); app = LivewireGUI(root); root.mainloop()
