# edge/edge_client.py
import socket
import time

from network_udp_retx import send_data


LOCAL_RECV_PORT = 5005        # Receiving PORT
LOCAL_SEND_PORT = 5006        # Sending PORT
DEST_PORT = 5006			  # Receiver's PORT
dest_addr = "192.168.0.157"  # Receiver's IP address (laptop)

FILE_PATH = "video.mp4"      # Path to the file to be sent
FILE_CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB, adjust as needed

# SERVER_IP = "192.168.0.157" # "10.53.6.127"
# SERVER_IP = "10.42.0.1"


def main():

    # Receiving socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("", LOCAL_RECV_PORT))

    # Sending socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.bind(("", LOCAL_SEND_PORT))  # Bind to a different port for sending

    FILE_SIZE = os.path.getsize(FILE_PATH)
    print(f"File size: {FILE_SIZE/(1024*1024):.3f} MB")

    total_chunks = (FILE_SIZE + FILE_CHUNK_SIZE - 1) // FILE_CHUNK_SIZE
    print(f"Total chunks to send: {total_chunks}")

    try:
        
        handshake = f"FILE_START:{total_chunks}".encode()
        send_sock.sendto(handshake, (dest_addr, DEST_PORT))
        # print(f"Handshake sent: {handshake.decode()}\n")

        t0 = time.perf_counter()

        with open(FILE_PATH, "rb") as file:
            chunk_index = 0
            while True:
                chunk_data = file.read(FILE_CHUNK_SIZE)
                if not chunk_data:
                    break  # End of file

                print(f"Sending chunk {chunk_index + 1}/{total_chunks}...")
                # payload = f"{chunk_index}/{total_chunks}".encode() + b"::" + chunk_data
                send_data(send_sock, chunk_data, (dest_addr, DEST_PORT), recv_sock)
                chunk_index += 1

        t1 = time.perf_counter()
        print("File sent successfully")

        msg, _ = recv_sock.recvfrom(1024)

        T_comm, T_latency = map(float, msg.decode().split(","))

        T_edge = t1 - t0

        T_comm_total = T_comm + T_latency

        print("Edge:", T_edge*1000, 'ms')
        print("Comm:", T_comm*1000, 'ms')
        print("Latency:", T_latency*1000, 'ms')
        print("Total comm:", T_comm_total*1000, 'ms')
        
    except OSError as e:
        print(f"Network error: {e}")
        print(f"Error code: {e.errno}")
        return
        
    # print("Sent")

    # msg, _ = recv_sock.recvfrom(1024)

    # T_comm, T_latency = map(float, msg.decode().split(","))

    # T_edge = t1 - t0

    # T_comm_total = T_comm + T_latency

    # print("Edge:", T_edge*1000, 'ms')
    # print("Comm:", T_comm*1000, 'ms')
    # print("Latency:", T_latency*1000, 'ms')
    # print("Total comm:", T_comm_total*1000, 'ms')

if __name__ == "__main__":
    main()