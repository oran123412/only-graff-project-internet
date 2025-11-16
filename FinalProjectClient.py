import socket
import os

SERVER_IP = "127.0.0.1"
SERVER_PORT = 1234
PACKET_SIZE = 1024

def run_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    filename = input("Enter filename: ")
    sock.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))

    response, _ = sock.recvfrom(2048)

    if response == b"NOT FOUND 404":
        print("File not found (404)")
        return
    else:
        print("Server accepted file request")

    received = {}
    expected = 0

    while True:
        packet, server = sock.recvfrom(2048)

        if packet == b"DONE":
            break

        header, data = packet.split(b"|", 1)
        seq = int(header.decode())

        print(f"Got packet seq={seq}")
        received[seq] = data

        sock.sendto(str(seq).encode(), server)  # שליחת ACK

    output = b""
    i = 0
    while i in received:
        output += received[i]
        i += 1

    out_name = "received_" + filename
    with open(out_name, "wb") as f:
        f.write(output)

    print(f"File saved as: {out_name}")

if __name__ == "__main__":
    run_client()
