import struct
import socket
import time


# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# # # Set buffers
# s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16*1024*1024)
# s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16*1024*1024)

# Check actual values
# print("RCVBUF:", s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
# print("SNDBUF:", s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))

CHUNK_SIZE = 4096
HEADER_FMT = "I"        # data packet header: packet_id
HEADER_SIZE = struct.calcsize(HEADER_FMT)
BUNCH_SIZE = 20

CONTROL_FMT = "I I d"     # control packet format: total_packets | BUNCH_SIZE | timestamp
CONTROL_SIZE = struct.calcsize(CONTROL_FMT)

ACK_FMT_BASE = "I I"     # ACK packet base format: bunch_id | num_missing
ACK_SIZE_BASE = struct.calcsize(ACK_FMT_BASE)


def send_ack(send_sock, addr, bunch_id, missing_packets):
    ack_fmt = "I I " + "I"*len(missing_packets)  # bunch_id | num_missing | missing_packet_ids...
    ack_packet = struct.pack(ack_fmt, bunch_id, len(missing_packets), *missing_packets)
    print(f"Sending ACK for bunch {bunch_id}. Missing packets: {missing_packets}")
    print(f"ACK packet content (hex): {ack_packet.hex()}")    
    send_sock.sendto(b"A" + ack_packet, addr)  # "A" = ACK packet marker

def receive_ack(recv_sock):
    
    recv_sock.settimeout(1)  # Set a short timeout for ACK reception
    try:
        while True:
            ack_packet, sender_addr_tuple = recv_sock.recvfrom(CHUNK_SIZE + ACK_SIZE_BASE + 100)
            if ack_packet[0:1] == b"A":
                ack_bunch_id, num_missing = struct.unpack("I I", ack_packet[1: 1+ACK_SIZE_BASE])
                missing_packet_ids = struct.unpack("I"*num_missing, ack_packet[1+ACK_SIZE_BASE: 1+ACK_SIZE_BASE+4*num_missing])
                print(f"ACK received for bunch {ack_bunch_id}. Missing packets: {missing_packet_ids}")
                return ack_bunch_id, num_missing, missing_packet_ids
            # else:
            #     print("Received non-ACK packet while waiting for ACK. Ignoring...")
                # return None, None, None
    except socket.timeout:
        print("ACK reception timed out")
        return None, -1, []             # Need to consider how to handle ACK timeout (retransmit, wait again,...)


def send_data(send_sock, payload, dest_addr_tuple, recv_sock):

    payload_size = len(payload)

    total_packets = (payload_size + CHUNK_SIZE - 1) // CHUNK_SIZE  
    print(f"Total pkts: {total_packets}")
    
    bunches = (total_packets + BUNCH_SIZE - 1) // BUNCH_SIZE
    
    send_start_time = time.time()

    # Send control packet first
    control_packet = struct.pack(CONTROL_FMT, total_packets, BUNCH_SIZE, send_start_time)
    send_sock.sendto(b"C" + control_packet, dest_addr_tuple)  # "C" = control packet marker

    # Send data packets in bunches    
    for BUNCH_ID in range(bunches):
        
        bunch_start = BUNCH_ID * BUNCH_SIZE
        bunch_end = min((BUNCH_ID + 1) * BUNCH_SIZE , total_packets)
        
        for packet_id in range(bunch_start,bunch_end):

            start = packet_id * CHUNK_SIZE
            end = start + CHUNK_SIZE        # This variable can be removed later, just for clarity now
            chunk = payload[start:end]
            header = struct.pack(HEADER_FMT, packet_id)

            send_sock.sendto(b"D" + header + chunk, dest_addr_tuple)    # "D" = data packet marker
            
            if packet_id == (total_packets - 1):
                print("All pkts sent, waiting for ACKs...")
                break
            
        # Check for ACKs and retransmit if needed

        print(f"Pkts sent for Bunch ID: {BUNCH_ID}, waiting for ACKs...")

        # ACK reception and retransmission loop for the current bunch
        while True:

            ack_bunch_id, num_missing, missing_packet_ids = receive_ack(recv_sock)
            print(f"Bunch ID: {ack_bunch_id}, # missing pkt: {num_missing}, ID of missing pkts: {missing_packet_ids}")
            
            # if num_missing != len(missing_packet_ids):
            #     print("Warning: ACK inconsistency detected!")

            if not missing_packet_ids and num_missing == -2:
                print("Control packet retransmission requested by receiver, resending control packet...")
                control_packet = struct.pack(CONTROL_FMT, total_packets, BUNCH_SIZE, send_start_time)
                send_sock.sendto(b"C" + control_packet, dest_addr_tuple)  # "C" = control packet marker
                continue  # After retransmitting the control packet, wait for ACKs again

            if not missing_packet_ids and num_missing == 0:
                print(f"All pkts for Bunch ID: {ack_bunch_id} acknowledged, moving to next bunch...")
                break

            # ACK timeout or error case, we can choose to retransmit the whole bunch or just wait again for ACKs. 
            # Here we choose to retransmit the whole bunch for simplicity.
            if not missing_packet_ids and num_missing == -1:
                print(f"All pkts for Bunch ID: {BUNCH_ID} assumed lost due to ACK timeout, retransmitting whole bunch...")
                for packet_id in range(bunch_start,bunch_end):

                    start = packet_id * CHUNK_SIZE
                    end = start + CHUNK_SIZE        # This variable can be removed later, just for clarity now
                    chunk = payload[start:end]
                    header = struct.pack(HEADER_FMT, packet_id)

                    send_sock.sendto(b"D" + header + chunk, dest_addr_tuple)    # "D" = data packet marker
                    print(f"Retransmitted pkt id: {packet_id}")

                continue  # After retransmitting the whole bunch, wait for ACKs again

            else:
                print(f"Retransmitting {num_missing} missing pkts for Bunch ID: {BUNCH_ID}...")
                for packet_id in missing_packet_ids:
                    start = packet_id * CHUNK_SIZE
                    end = start + CHUNK_SIZE
                    chunk = payload[start:end]
                    header = struct.pack(HEADER_FMT, packet_id)
                    send_sock.sendto(b"D" + header + chunk, dest_addr_tuple)    # "D" = data packet marker
                    print(f"Retransmitted pkt id: {packet_id}")
        
    print("All pkts sent")

def receive_data(recv_sock, send_sock, DEST_PORT):

    recv_sock.settimeout(None)  # Ensure we're in blocking mode for the main reception loop
    packets = {}
    bunch_buffer = {}           # Temporary dictionary buffer to hold packets for each bunch until we can check for missing ones
    acked_bunches = set()       # Set to track which bunches have been ACKed

    CONTROL_FLAG = False
    total_packets = None
    recv_bunch_size = None
    t_first = None
    t_first_recv = None
    t_first_precise = None
    sender_addr_tuple = None

    while True:     #Keeping the receiver alive after timeout  

        try:
            while True:
                
                packet, sender_addr_tuple = recv_sock.recvfrom(CHUNK_SIZE + HEADER_SIZE + 100)

                packet_type = packet[0:1]          

                # For control packets, extract total_packets, recv_bunch_size, and timestamp
                if packet_type == b"C":
                    CONTROL_FLAG = True
                    recv_sock.settimeout(1)  # Set a short timeout for data reception
                    total_packets, recv_bunch_size, t_first = struct.unpack(CONTROL_FMT, packet[1 : 1+CONTROL_SIZE])
                    print(f"Control packet received. Total packets: {total_packets}, Bunch size: {recv_bunch_size}, Timestamp: {t_first:.6f}")
                    t_first_recv = time.time()                      # Timestamp when control packet is received
                    t_first_precise = time.perf_counter()           # High-resolution timestamp for comm time measurement

                # For data packets, extract packet_id and data, and store in buffer
                elif packet_type == b"D":
                    packet_id = struct.unpack(HEADER_FMT, packet[1: 1+HEADER_SIZE])[0]
                    data = packet[1+HEADER_SIZE : 1+HEADER_SIZE+CHUNK_SIZE]
                    # print(f"Data packet received. Packet ID: {packet_id}, Size: {len(data)} bytes")
                    # ACK_FLAG = False

                    if CONTROL_FLAG:

                        bunch_id = packet_id // recv_bunch_size

                        if bunch_id not in bunch_buffer:
                            bunch_buffer[bunch_id] = {}         # Initialize buffer for this bunch

                        bunch_buffer[bunch_id][packet_id] = data
                        print(f"Packet ID {packet_id} stored in bunch buffer for bunch {bunch_id}. Current buffer keys: {bunch_buffer[bunch_id].keys()}")

                        is_full_bunch = len(bunch_buffer[bunch_id]) == recv_bunch_size
                        is_last_packet = packet_id == (total_packets - 1)

                        # Check for missing packets in the bunch and send ACKs
                        # If we have a full bunch or it's the last packet, check for missing ones and send ACK if needed
                        if (is_full_bunch or is_last_packet) and bunch_id not in acked_bunches:   

                            expected_packet_ids = set(range(bunch_id*recv_bunch_size, min((bunch_id+1)*recv_bunch_size, total_packets)))                
                            missing = expected_packet_ids - set(bunch_buffer[bunch_id].keys()) 
                            print(f"Sending ACK for bunch {bunch_id}. Missing packets: {missing}")
                            send_ack(send_sock, (sender_addr_tuple[0], DEST_PORT), bunch_id, list(missing))
                            acked_bunches.add(bunch_id)  # Mark this bunch as ACKed to avoid duplicate ACKs
                            print(f"bunch buffer for bunch {bunch_id}: {bunch_buffer[bunch_id].keys()}")

                            if len(missing) == 0 and not missing and bunch_id in acked_bunches:
                                packets.update(bunch_buffer[bunch_id])      # Move received packets from bunch buffer to main packets dictionary
                                del bunch_buffer[bunch_id]                  # Clear buffer for this bunch after all pkts received and ACK sent
                                acked_bunches.discard(bunch_id)              # Remove from ACKed set to allow for potential future ACKs if needed
                                print("========================================")
                        
                        if len(packets) == total_packets:
                            print("All packets received, exiting reception loop.")
                            break
                        
                    else:
                        print("Data packet received before control packet. Ignoring...")
                        # Send ACK to retransmit the control packet
                        if sender_addr_tuple:
                            print("Requesting retransmission of control packet...")
                            send_ack(send_sock, (sender_addr_tuple[0], DEST_PORT), -2, [0])  # Using bunch_id=0 and missing_packet_id=0 to indicate control packet retransmission request
                
                else:
                    print("Unknown packet type received. Ignoring...")
            
            
            recv_sock.settimeout(None)  # Remove timeout for final reception phase     

            print(f"First packet timestamp: {t_first:.6f} seconds")
            print(f"First packet received at: {t_first_recv:.6f} seconds")

            T_latency = (t_first_recv - t_first) * 1000.000
            print(f"Latency from first packet sent to first packet received: {T_latency:.6f} ms")
            
            t_last = time.perf_counter()

            T_comm = (t_last - t_first_precise) * 1000.000

            print(f"All pkts received in {T_comm:.6f} ms")

            ordered = [packets[i] for i in range(total_packets)]

            data = b"".join(ordered)

            return data, sender_addr_tuple, T_comm, T_latency

        except socket.timeout:
            print("Reception timed out")
            # Only send ACK if we have context
            if sender_addr_tuple and total_packets is not None:
                # If we have a control packet, we can still send an ACK for the last bunch we were working on, even if we haven't received all packets yet
                if bunch_buffer: 
                    bunch_id = list(bunch_buffer.keys())[-1] 
                else:
                    bunch_id = None
                    
                if bunch_id is not None:
                    expected = set(range(bunch_id * recv_bunch_size, min((bunch_id + 1) * recv_bunch_size, total_packets)))
                    missing = expected - set(bunch_buffer.get(bunch_id, {}).keys())
                    send_ack(send_sock, (sender_addr_tuple[0], DEST_PORT), bunch_id, list(missing))

        except KeyboardInterrupt:
            print("\n\nServer shutting down...")
            recv_sock.close()
            print("Socket closed. Goodbye!")