import json
import sys
import bencodepy
import hashlib as hs
import requests
import socket
import os
import struct
from urllib.parse import urlparse, parse_qs
# from concurrent.futures import ThreadPoolExecutor

decoder = bencodepy.Bencode(encoding='utf-8')


def decode_bencode(bencoded_value):
    return decoder.decode(bencoded_value)


def decode_torrent(torrent_file):
    with open(torrent_file, "rb") as f:
        torrent_data = f.read()
        metadata = bencodepy.decode(torrent_data)
        # print(metadata)

        info_hash = hs.sha1(bencodepy.encode(metadata[b'info'])).hexdigest()
        info_hash_encoded = hs.sha1(bencodepy.encode(metadata[b'info'])).digest()
        tracker = metadata[b'announce'].decode("utf-8")
        length = metadata[b'info'][b'length']
        piece_length = metadata[b'info'][b'piece length']
        pieces = metadata[b'info'][b'pieces']
        hashes_hex = [pieces[i:i + 20].hex() for i in range(0, len(pieces), 20)]
        hashes = [pieces[i:i + 20] for i in range(0, len(pieces), 20)]

    return info_hash, info_hash_encoded, tracker, length, piece_length, hashes, hashes_hex


def decode_peers(info_hash, tracker, length):

    tracker_response = requests.get(tracker, params={
        "info_hash": info_hash,
        "peer_id": "testpeerforchallenge",
        "port": 6881,
        "uploaded": 0,
        "downloaded": 0,
        "left": length,
        "compact": 1
    })

    peer_info = bencodepy.decode(tracker_response.content)[b'peers']
    if not peer_info:
        raise ValueError("No peers found in tracker response")

    peers = []
    for i in range(0, len(peer_info), 6):
        peer = peer_info[i: i + 6]
        ip_address = f"{peer[0]}.{peer[1]}.{peer[2]}.{peer[3]}"
        port = int.from_bytes(peer[4:], byteorder="big", signed=False)
        peers.append(f"{ip_address}:{port}")

    return peers


def perform_handshake(ip, port, info_hash, extension_support=False):

    if extension_support:
        reserved = b'\x00\x00\x00\x00\x00\x10\x00\x00'
    else:
        reserved = b'\x00' * 8

    client_handshake = (bytes([19])
                        + b'BitTorrent protocol'
                        + reserved
                        + info_hash
                        + b'testpeerforchallenge')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, int(port)))
    s.sendall(client_handshake)

    return s, s.recv(68)


def receive_message(s):
    length = s.recv(4)
    while not length or not int.from_bytes(length):
        length = s.recv(4)
    message = s.recv(int.from_bytes(length))

    while len(message) < int.from_bytes(length):
        chunk = s.recv(int.from_bytes(length) - len(message))
        if not chunk:
            raise ConnectionError("Connection lost during message reception")
        message += chunk
    return length + message


def verify_message(message, message_id):
    if message[4] != message_id:
        raise ValueError(
            "Expected message of id %s, but received id %s" % (message_id, message[4])
        )
    if int.from_bytes(message[:4]) != len(message[4:]):
        raise ValueError("Message wrong length.")


def construct_message(message_id, payload):
    message_id = message_id.to_bytes(1)
    message = message_id + payload
    length = len(message)
    length_prefix = length.to_bytes(4, byteorder="big")
    message = length_prefix + message
    return message


def request_block(s, piece_index, block_index, length):
    index = piece_index
    begin = block_index * 2 ** 14
    length = length
    payload = (
            struct.pack(">I", index) + struct.pack(">I", begin) + struct.pack(">I", length)
    )
    message = construct_message(6, payload)
    s.send(message)
    piece_message = receive_message(s)
    while piece_message[4] != 7:
        piece_message = receive_message(s)
    # Verify that the block has the payload we expect:
    verify_message(piece_message, 7)
    received_index = int.from_bytes(piece_message[5:9])
    received_begin = int.from_bytes(piece_message[9:13])
    if received_index != index or received_begin != begin:
        raise ValueError("Piece message does not have expected payload.")
    block = piece_message[13:]
    return block


def download_piece(s, length, piece_length, pieces_list, outputfile, piececount):
    bitfield = receive_message(s)
    verify_message(bitfield, 5)

    interested = construct_message(2, b"")
    s.send(interested)

    # Wait for unchoke message
    unchoke = receive_message(s)
    while unchoke[4] != 1:
        unchoke = receive_message(s)
    verify_message(unchoke, 1)

    # Calculate number of blocks, figuring out if we are the last piece
    last_piece_remainder = length % piece_length
    total_pieces = len(pieces_list)

    if piececount + 1 == total_pieces and last_piece_remainder > 0:
        length = last_piece_remainder
    else:
        length = piece_length
    block_size = 16 * 1024
    full_blocks = length // block_size
    final_block = length % block_size

    piece = b""
    sha1hash = hs.sha1()
    try:
        if full_blocks == 0:
            block = request_block(s, piececount, 0, final_block)
            piece += block
            sha1hash.update(block)
        else:
            for i in range(full_blocks):
                block = request_block(s, piececount, i, block_size)
                piece += block
                sha1hash.update(block)
            if final_block > 0:
                block = request_block(s, piececount, i + 1, final_block)
                piece += block
                sha1hash.update(block)
    except (ConnectionError, socket.timeout) as e:
        print(f"Error downloading block: {e}")
        s.close()
        return None

    s.close()

    # Verify piece hash
    piece_hash = pieces_list[piececount]
    local_hash = sha1hash.digest()
    if piece_hash != local_hash:
        raise ValueError("Piece hash mismatch.")

    with open(outputfile, "wb") as piece_file:
        piece_file.write(piece)

    print(f"Downloaded piece_{piececount} at path: {outputfile}")
    return outputfile


# Multithreaded download helper function
def download_piece_wrapper(args):
    peer_ip, peer_port, info_hash, length, piece_length, pieces_list, piece_idx = args
    socket_obj, _ = perform_handshake(peer_ip, peer_port, info_hash)
    output_file = f"./tmp/test-{piece_idx}"
    print(f"Downloading piece_{piece_idx}...")
    return download_piece(socket_obj, length, piece_length, pieces_list, output_file, piece_idx)


def download(torrent_file, outputfile):
    _, info_hash, tracker, length, piece_length, pieces_list, _ = decode_torrent(torrent_file)
    peer_ip, peer_port = decode_peers(info_hash, tracker, length)[0].split(":")
    total_pieces = len(pieces_list)

    print("Total pieces:", total_pieces)

    # Sequential Download
    piece_files = []
    for piece_idx in range(0, total_pieces):
        print(f"Downloading piece_{piece_idx}...")
        socket_obj, _ = perform_handshake(peer_ip, peer_port, info_hash)
        out = download_piece(socket_obj, length, piece_length, pieces_list, "/tmp/test-" + str(piece_idx), piece_idx)
        piece_files.append(out)

    with open(outputfile, "ab") as result_file:
        for piece_path in piece_files:
            with open(piece_path, "rb") as piece_file_obj:
                result_file.write(piece_file_obj.read())
            os.remove(piece_path)

'''
    ## Multithreaded download testing
    args = [
        (peer_ip, peer_port, info_hash, length, piece_length, pieces_list, piece_idx)
        for piece_idx in range(0, total_pieces)
    ]

    # Use ThreadPoolExecutor to download pieces in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        piece_files = list(executor.map(download_piece_wrapper, args))
'''


def magnet_parse(link):
    parsed = urlparse(link)

    query_params = parse_qs(parsed.query)

    info_hash = query_params.get('xt', [None])[0]
    if info_hash and info_hash.startswith('urn:btih:'):
        info_hash = info_hash.split(':')[-1]

    tracker_url = query_params.get('tr', [None])[0]

    return tracker_url, info_hash


def magnet_handshake(link):
    tracker, info_hash = magnet_parse(link)
    encoded_info_hash = bytes.fromhex(info_hash)
    peer_ip, peer_port = decode_peers(encoded_info_hash, tracker, 999)[0].split(":")
    _, peer_data = perform_handshake(peer_ip, peer_port, encoded_info_hash, True)

    print(f"Peer ID: {peer_data[48:].hex()}")


def main():
    command = sys.argv[1]

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        def bytes_to_str(data):
            if isinstance(data, bytes):
                return data.decode()
            raise TypeError(f"Type not serializable: {type(data)}")

        print(json.dumps(decode_bencode(bencoded_value), default=bytes_to_str))

    elif command == "info":
        info_hash, _, tracker, length, piece_length, _, hashes = decode_torrent(sys.argv[2])

        print("Tracker URL:", tracker)
        print("Length:", length)
        print("Info Hash:", info_hash)
        print("Piece Length:", piece_length)
        print("Piece Hashes:")
        for item in hashes:
            print(item)

    elif command == "peers":
        _, info_hash, tracker, length, _, _, _ = decode_torrent(sys.argv[2])
        peers = decode_peers(info_hash, tracker, length)
        for i in range(len(peers)):
            print(peers[i])

    elif command == "handshake":
        _, info_hash, _, _, _, _, _ = decode_torrent(sys.argv[2])
        ip, port = sys.argv[3].split(":")

        _, peer_id = perform_handshake(ip, port, info_hash)
        print(f"Peer ID: {peer_id[48:].hex()}")

    elif command == "download_piece":
        _, info_hash, tracker, length, piece_length, pieces_list, _ = decode_torrent(sys.argv[4])
        peer_ip, peer_port = decode_peers(info_hash, tracker, length)[0].split(":")
        socket_obj, _ = perform_handshake(peer_ip, peer_port, info_hash)

        save_location = sys.argv[3]
        piece_idx = sys.argv[5]
        _ = download_piece(socket_obj, length, piece_length, pieces_list, save_location, int(piece_idx))

    elif command == "download":
        save_location = sys.argv[3]
        download(sys.argv[4], save_location)

    elif command == "magnet_parse":
        link, info_hash = magnet_parse(sys.argv[2])
        print(f"Tracker URL: {link}")
        print(f"Info Hash: {info_hash}")

    elif command == "magnet_handshake":
        magnet_handshake(sys.argv[2])

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
