This folder contains python code files that implements UDP based retransmission framework.

**network_udp_retx.py**

This file implements functions to send UDP packets, receive UDP packets, send acknowledgments and receive acknowledgements

  **send_ack:** Sends acknowledgment packets containing the missing packets.
  
  **receive_ack:** Detects if the receive ACK packet is for Control packet or Data packet and acts accordingly.
  
  **send_data:** Divides the payload data into appropriate number of chunks and sends it after appending it with the packet IDs. Once the data is sent, it waits for the ACK and after checking for the missing packet IDs it will re-transmit the missing packets if needed.
  
  **receive_data:** Receives the packets and identifies the packet type. Saves the received data in a buffer and at the end checks for the missing packets, and triggers the ACK accordingly.
