import socket
import os
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading

# === LIVE GRAPH DATA ===
live_window = []

# === SERVER SETTINGS ===
SERVER_IP = "127.0.0.1"
SERVER_PORT = 1234
FILE_DIR = r"C:\Users\oranm\AppData\Local\Programs\Python\Python313\python\Almog\files"

PACKET_SIZE = 8192
TIMEOUT = 0.4
THRESHOLD = 8


# === Create Packet Function ===
def make_packet(seq, data):
    return f"{seq}|".encode() + data


# === Real-time Graph Function (RUNS ON MAIN THREAD) ===
def live_plot():
    plt.style.use("ggplot")

    fig, ax = plt.subplots()
    ax.set_title("RUDP Congestion Window (LIVE)")
    ax.set_xlabel("Update #")
    ax.set_ylabel("Window Size")

    is_paused = False   # משתנה פנימי

    # --- עדכון גרף ---
    def update(frame):
        if is_paused:
            return

        ax.clear()
        ax.plot(live_window, marker='o')
        ax.set_title("RUDP Congestion Window (LIVE)")
        ax.set_xlabel("Update #")
        ax.set_ylabel("Window Size")

    # --- יצירת האנימציה (חשוב לשמור את anim) ---
    anim = FuncAnimation(fig, update, interval=300)

    # --- כפתור Pause ---
    def toggle_pause(event):
        nonlocal is_paused
        if event.key == " ":
            is_paused = not is_paused
            if is_paused:
                anim.event_source.stop()
                print("Paused")
            else:
                anim.event_source.start()
                print("Running")

    fig.canvas.mpl_connect("key_press_event", toggle_pause)

    plt.show()



# === RUDP SERVER (RUNS ON SECOND THREAD) ===
def run_server():
    global THRESHOLD

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.settimeout(None)

    print("SERVER READY...")

    while True:
        try:
            print("Waiting for request...")
            request, client = sock.recvfrom(65536)
            print("Got request:", request)

            filename = request.decode().strip()
            print(f"Client requested: {filename}")

            # Check if file exists
            path = os.path.join(FILE_DIR, filename)
            if not os.path.exists(path):
                sock.sendto(b"NOT FOUND 404", client)
                print("FILE NOT FOUND:", filename)
                continue

            sock.sendto(b"OK", client)

            # Load file
            with open(path, "rb") as f:
                data = f.read()

            packets = [
                data[i:i + PACKET_SIZE]
                for i in range(0, len(data), PACKET_SIZE)
            ]

            window = 1
            next_seq = 0
            base = 0
            acked = set()

            live_window.append(window)

            print(f"Starting RUDP transfer ({len(packets)} packets)...")

            while base < len(packets):

                for seq in range(next_seq, min(base + window, len(packets))):
                    print(f"Sending seq {seq}   window={window}")
                    sock.sendto(make_packet(seq, packets[seq]), client)

                next_seq = min(base + window, len(packets))

                try:
                    ack_raw, _ = sock.recvfrom(65536)
                    ack = int(ack_raw.decode())
                    print(f"ACK received: {ack}")

                    if ack not in acked:
                        acked.add(ack)

                        if ack == base:
                            while base in acked:
                                base += 1

                        # Increase window
                        if window < THRESHOLD:
                            window *= 2
                        else:
                            window += 1

                        # Update graph
                        live_window.append(window)

                except socket.timeout:
                    print("TIMEOUT → window reset to 1")
                    THRESHOLD = max(1, window // 2)
                    window = 1
                    next_seq = base
                    live_window.append(window)

            sock.sendto(b"DONE", client)
            print("Finished sending file!")
            # Reset only RUDP state, keep graph history
            window = 1
            next_seq = 0
            base = 0
            acked = set()


        except Exception as e:
            print("ERROR:", e)


# === MAIN ===
if __name__ == "__main__":
    # Run server on background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Run graph on main thread
    live_plot()

#python server.py
