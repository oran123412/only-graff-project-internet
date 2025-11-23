import socket
import os

SERVER_IP = "127.0.0.1"
SERVER_PORT = 1234
PACKET_SIZE = 8192

def run_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    filename = input("Enter the filename you want to request: ").strip()
    sock.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))

    # === קבלת תגובה ראשונית מהשרת ===
    try:
        response, _ = sock.recvfrom(65536)
    except socket.timeout:
        print("No response from server (timeout on initial response).")
        return

    if response == b"NOT FOUND 404":
        print("File not found (404)")
        return
    else:
        print("Server accepted file request")

    received = {}

    while True:
        packet, server = sock.recvfrom(65536)

        if packet == b"DONE":
            break

        # בדיקה שהפקטה תקינה בכלל
        if b"|" not in packet:
            continue

        header, data = packet.split(b"|", 1)

        try:
            seq = int(header.decode())
        except:
            continue

        # *** תמיד שולחים ACK — גם אם זה כפול ***
        sock.sendto(str(seq).encode(), server)

        # מוסיפים רק אם זה חדש
        if seq not in received:
            print(f"Got new packet seq={seq}")
            received[seq] = data
        else:
            print(f"Duplicate packet seq={seq} (ACK re-sent)")

    # === בניית הקובץ מחדש ===
    output = b""
    i = 0
    while i in received:
        output += received[i]
        i += 1

    out_name = "received_" + filename
    with open(out_name, "wb") as f:
        f.write(output)

    print(f"\nFile saved as: {out_name}")

    # === פתיחה אוטומטית ===
    try:
        os.startfile(out_name)
    except:
        print("Couldn't open file automatically.")

if __name__ == "__main__":
    run_client()



#python client.py

