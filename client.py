import socket
import os

SERVER_IP = "127.0.0.1"
SERVER_PORT = 1234
PACKET_SIZE = 8192   # מתאים לסרטונים ותמונות

def run_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    filename = input("Enter filename: ").strip()
    sock.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))

    response, _ = sock.recvfrom(65536)

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

        header, data = packet.split(b"|", 1)
        seq = int(header.decode())

        print(f"Got packet seq={seq}")
        received[seq] = data

        sock.sendto(str(seq).encode(), server)  # ACK

    # בניית הקובץ מחדש לפי סדר
    output = b""
    i = 0
    while i in received:
        output += received[i]
        i += 1

    # שמירה
    out_name = "received_" + filename
    with open(out_name, "wb") as f:
        f.write(output)

    print(f"File saved as: {out_name}")

    # פתיחת הקובץ אוטומטית
    try:
        os.startfile(out_name)
    except:
        print("Couldn't open file automatically.")

if __name__ == "__main__":
    run_client()
#python client.py

