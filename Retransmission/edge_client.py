# edge/edge_client.py
import socket
import time
import torch

from models import load_model
from splitter import SplitModel
from serializer import serialize_tensor
from network_udp_retx import send_data


LOCAL_RECV_PORT = 5005        # Receiving PORT
LOCAL_SEND_PORT = 5006        # Sending PORT
DEST_PORT = 5006			  # Receiver's PORT
dest_addr = "192.168.0.157"  # Receiver's IP address (laptop)


# SERVER_IP = "192.168.0.157" # "10.53.6.127"
# SERVER_IP = "10.42.0.1"


def main():

    # Receiving socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("", LOCAL_RECV_PORT))

    # Sending socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.bind(("", LOCAL_SEND_PORT))  # Bind to a different port for sending

    model = load_model()

    split_idx = 5

    split = SplitModel(model, split_idx)

    x = torch.randn(1,3,224,224)

    t0 = time.perf_counter()

    act = split.edge_forward(x)

    t1 = time.perf_counter()

    payload = serialize_tensor(act)
    
#     print("Ready to send")

    try:
        send_data(send_sock, payload, (dest_addr, DEST_PORT), recv_sock)
        
    except OSError as e:
        print(f"Network error: {e}")
        print(f"Error code: {e.errno}")
        return
        
    print("Sent")

    msg, _ = recv_sock.recvfrom(1024)

    T_comm, T_latency = map(float, msg.decode().split(","))

    T_edge = t1 - t0

    T_comm_total = T_comm + T_latency

    print("Edge:", T_edge*1000, 'ms')
    print("Comm:", T_comm*1000, 'ms')
    print("Latency:", T_latency*1000, 'ms')
    print("Total comm:", T_comm_total*1000, 'ms')

if __name__ == "__main__":
    main()