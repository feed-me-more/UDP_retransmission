# server/server_node.py

import socket
import time

from network_udp_retx import receive_data


LOCAL_RECV_PORT = 5006            # Receiving port
LOCAL_SEND_PORT = 5005            # Sending port
DEST_PORT = 5005                  # Receiver's port
dest_addr = "192.168.0.163"       # Receiver's IP address
# send_addr = "192.168.0.157"     # Sender's IP address

def main():

    # Receiving socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("", LOCAL_RECV_PORT))

    # Sending socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.bind(("", LOCAL_SEND_PORT))  # Bind to a different port for sending

    print("Server ready")
    print("Press Ctrl+C to stop the server\n")

    try:
        while True: 

            print("Waiting for activation...")

            while True:
                result = receive_data(recv_sock, send_sock, DEST_PORT)

                if result is not None:
                    data, sender_addr_tuple, T_comm, T_latency = result
                    break
                    
            print("File received")

            with open("received_video.mp4", "wb") as file:
                file.write(data)

            # activation = deserialize_tensor(data)

            # t0 = time.perf_counter()

            # out = split.server_forward(activation)

            # t1 = time.perf_counter()

            # T_server = t1 - t0

            msg = f"{T_comm},{T_latency}"

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