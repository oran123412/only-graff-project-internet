import socket
import os
import random
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
TIMEOUT = 0.4          # זמן המתנה התחלתי ל-ACK
THRESHOLD = 8          # ssthresh התחלתי

def make_packet(seq, data):
    return f"{seq}|".encode() + data

# === GRAPH ===
def live_plot():
    plt.style.use("ggplot")
    fig, ax = plt.subplots()
    ax.set_title("RUDP Congestion Window (LIVE)")
    ax.set_xlabel("Update #")
    ax.set_ylabel("Window Size")

    is_paused = False

    def update(frame):
        if is_paused:
            return
        ax.clear()
        ax.plot(live_window, marker='o')
        ax.set_title("RUDP Congestion Window (LIVE)")
        ax.set_xlabel("Update #")
        ax.set_ylabel("Window Size")

    # cache_frame_data=False כדי להעלים את ה־warning של matplotlib
    anim = FuncAnimation(fig, update, interval=300, cache_frame_data=False)

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

# === RUDP SERVER ===
def run_server():
    global THRESHOLD, TIMEOUT

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.settimeout(None)       # ממתינים ללקוח בלי timeout
    print(f"SERVER READY on {SERVER_IP}:{SERVER_PORT}\n")

    while True:
        try:
            print("Waiting for client request...")
            request, client = sock.recvfrom(65536)
            filename = request.decode().strip()
            print(f"Client requested: {filename}")

            # === בחירת איבוד פקטות ב-Download הזה בלבד ===
            SIMULATE_LOSS = False
            LOSS_PERCENTAGE = 0
            choice = input("Simulate packet loss? (y/n): ").strip().lower()
            if choice == "y":
                SIMULATE_LOSS = True
                while True:
                    try:
                        LOSS_PERCENTAGE = int(input("Loss percentage (0-100): ").strip())
                        if 0 <= LOSS_PERCENTAGE <= 100:
                            break
                    except:
                        pass
                print(f"Packet loss simulation ON → {LOSS_PERCENTAGE}%\n")
            else:
                print("Packet loss simulation OFF\n")

            # === בדיקת קובץ ===
            path = os.path.join(FILE_DIR, filename)
            if not os.path.exists(path):
                sock.sendto(b"NOT FOUND 404", client)
                print("FILE NOT FOUND:", filename)
                continue

            sock.sendto(b"OK", client)

            with open(path, "rb") as f:
                data = f.read()

            packets = [data[i:i + PACKET_SIZE] for i in range(0, len(data), PACKET_SIZE)]
            window = 1
            base = 0
            next_seq = 0
            acked = set()
            live_window.append(window)

            print(f"Starting RUDP transfer ({len(packets)} packets)...")

            # משתמשים ב-timeout רק אם יש סימולציה
            if SIMULATE_LOSS:
                sock.settimeout(TIMEOUT)
            else:
                sock.settimeout(None)

            retry_count = 0
            MAX_RETRIES = 20  # כמה ניסיונות לפני שמתייאשים

            while base < len(packets):

                for seq in range(next_seq, min(base + window, len(packets))):
                    # סימולציה: לא משדרים חלק מהפקטות
                    if SIMULATE_LOSS and random.randint(1, 100) <= LOSS_PERCENTAGE:
                        print(f"⚠ Lost seq={seq}")
                        continue

                    sock.sendto(make_packet(seq, packets[seq]), client)
                    print(f"📤 Sent seq={seq} window={window}")

                next_seq = min(base + window, len(packets))

                try:
                    ack_raw, _ = sock.recvfrom(65536)
                    ack = int(ack_raw.decode())
                    print(f"📥 ACK={ack}")

                    if ack not in acked:
                        acked.add(ack)
                        retry_count = 0  # קיבלנו ACK → מאפסים נסיונות

                        if ack == base:
                            while base in acked:
                                base += 1

                        # גידול חלון - slow start ואז AIMD
                        if window < THRESHOLD:
                            window *= 2
                        else:
                            window += 1
                        live_window.append(window)

                        # אם TIMEOUT גדל בעבר, אפשר בעדינות להקטין קצת
                        if SIMULATE_LOSS and TIMEOUT > 0.4:
                            TIMEOUT = max(0.4, TIMEOUT * 0.8)
                            sock.settimeout(TIMEOUT)

                except (socket.timeout, ConnectionResetError):
                    retry_count += 1
                    print(f"⏱ TIMEOUT/RESET! retry={retry_count}, base={base}, window={window}")

                    THRESHOLD = max(1, window // 2)
                    window = 1
                    next_seq = base
                    live_window.append(window)

                    # Exponential backoff לטובת רשת עם איבוד גבוה
                    if SIMULATE_LOSS:
                        TIMEOUT = min(TIMEOUT * 2, 5.0)
                        sock.settimeout(TIMEOUT)
                        print(f"⌛ New TIMEOUT = {TIMEOUT:.2f} sec")

                    if retry_count >= MAX_RETRIES:
                        print("⚠ Too many retries, aborting this transfer.")
                        break

            # סיום העברה (או ביטול)
            sock.settimeout(None)       # מחזירים מצב רגיל

            if base >= len(packets):
                sock.sendto(b"DONE", client)
                print("🎉 Transfer complete!\n")
            else:
                sock.sendto(b"DONE", client)
                print("⚠ Transfer aborted (not all packets delivered).\n")

            # ==== RESET SAFE STATE לכל הורדה חדשה ====
            THRESHOLD = 8
            TIMEOUT = 0.4
            live_window.append(1)       # מסמן התחלה חדשה בגרף

        except Exception as e:
            print("ERROR:", e)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    live_plot()


#python server.py
