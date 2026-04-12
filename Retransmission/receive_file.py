import socket
import time

from network_udp_retx import receive_data


LOCAL_RECV_PORT = 5006            # Receiving port
LOCAL_SEND_PORT = 5005            # Sending port
DEST_PORT = 5005                  # Receiver's port
dest_addr = "192.168.0.163"       # Sender's IP address (R-pi)
# send_addr = "192.168.0.157"     # Receiver's IP address (laptop)

def main():

    # Receiving socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("", LOCAL_RECV_PORT))

    # Sending socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.bind(("", LOCAL_SEND_PORT))  # Bind to a different port for sending

    print("Server ready")
    print("Press Ctrl+C to stop the server\n")
    print("Waiting for file...")

    try:
        while True: 

            msg_encoded, sender_addr_tuple = recv_sock.recvfrom(1024)
            msg = msg_encoded.decode()

            if not msg.startswith("FILE_START:"):
                print(f"Received unexpected message: {msg}")
                continue

            total_chunks = int(msg.split(":")[1])
            print(f"Handshake received: {msg}")
            print(f"Expecting {total_chunks} chunks\n")

            T_comm_total = 0.0
            T_latency_total = 0.0

            for chunk_id in range(total_chunks):
                print(f"Waiting for chunk {chunk_id + 1}/{total_chunks}...")

                result = None

            # while True:
            #     result = receive_data(recv_sock, send_sock, DEST_PORT)

                while result is None:
                    result = receive_data(recv_sock, send_sock, DEST_PORT)

                data, sender_addr_tuple, T_comm, T_latency = result

                T_comm_total += T_comm
                T_latency_total += T_latency

                mode = "wb" if chunk_id == 0 else "ab"

                with open("received_video.mp4", mode) as file:
                    file.write(data)

            msg = f"{T_comm_total},{T_latency_total}"

            print("Sending results back")

            send_sock.sendto(msg.encode(), (sender_addr_tuple[0], DEST_PORT))

            print("Done\n")

    except KeyboardInterrupt:
        print("\n\nServer shutting down...")
        send_sock.close()
        recv_sock.close()
        print("Sockets closed. Goodbye!")


if __name__ == "__main__":
    main()