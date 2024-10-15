# BitTorrent in Python

> This BitTorrent program implements various functionalities for handling magnet links and torrent files, including downloading pieces, parsing magnet links, and peer communication using the `Bittorrent Peer Protocol`.

### Prerequisites

- Python 3.11+
- Pipenv
  ```bash
  pip install pipenv
  
  # Check if correctly installed
  pipenv --version
  ```

## Table of Contents

- [Setup](#setup)
- [Commands](#commands)

## Setup

1. Clone the repository and ensure you have the necessary dependencies installed.

    ```bash
    git clone https://github.com/sourasishbasu/bittorrent-python.git
    cd bittorrent-python/
    ```

2. Set up a Python virtual environment and install packages with `pipenv`:
   ```bash
   pipenv install
   pipenv shell
   ```

## Usage

You can run the program using the following command:

```bash
./your_bittorrent.sh <command> [options]
```

> [!NOTE]  
> Switch to `python app/main.py` instead of `./your_bittorrent.sh` if executing on Windows

#### Libraries Used

- `bencode.py` - To parse, decode and encode **bencode** format data
- `urllib` - Parsing magnet links
- `requests` - Sending **GET** requests to the torrent trackers
- Standard Libraries
  - `socket`
  - `sys`
  - `os`
  - `hashlib`
  - `struct`

### Commands

#### `magnet_handshake`
   - **Description**: Initiates a handshake with a peer using a magnet link announcing extension support.
   - **Parameters**: 
     - `magnet_link`: The magnet link to use for the handshake.
    
   - **Example**:
      ```bash
      ./your_bittorrent.sh magnet_handshake "magnet:?xt=urn:btih:c5fb9894bdaba464811b088d806bdd611ba490af&dn=magnet3.gif&tr=http%3A%2F%2F127.0.0.1:38961%2Fannounce"
      ```
   - **Expected Output**:
     ```
     Peer ID: 566d0e67e53794c815501f6b0eab681505d9e40b
     ```

#### `magnet_parse`
   - **Description**: Parses a magnet link and extracts its components.
   - **Parameters**:
     - `magnet_link`: The magnet link to parse.
   
   - **Example**:
     ```bash
     ./your_bittorrent.sh magnet_parse "magnet:?xt=urn:btih:3f994a835e090238873498636b98a3e78d1c34ca&dn=magnet2.gif&tr=http%3A%2F%2Fbittorrent-test-tracker.codecrafters.io%2Fannounce"
     ```
     
   - **Expected Output**:
     ```bash
     Tracker URL: http://bittorrent-test-tracker.codecrafters.io/announce
     Info Hash: 3f994a835e090238873498636b98a3e78d1c34ca
     ```

#### `download`
   - **Description**: Downloads the entire file from the specified torrent.
   - **Parameters**:
     - `-o <output_file>`: The path where the downloaded file will be saved.
     - `<torrent_file>`: The path to the torrent file.

   - **Example**:
     ```bash
     ./your_bittorrent.sh download -o /tmp/torrents4241288447/congratulations.gif /tmp/torrents4241288447/congratulations.gif.torrent
     ```
     
   - **Expected Output**:
     ```bash
     Total pieces: 4
     Downloading piece_0...
     Downloaded piece_0 at path: /tmp/test-0
     Downloading piece_1...
     Downloaded piece_1 at path: /tmp/test-1
     Downloading piece_2...
     Downloaded piece_2 at path: /tmp/test-2
     Downloading piece_3...
     Downloaded piece_3 at path: /tmp/test-3
     ```

#### `download-piece`
   - **Description**: Downloads a specific piece of a file from a torrent.
   - **Parameters**:
     - `-o <output_file>`: The path where the downloaded piece will be saved.
     - `<torrent_file>`: The path to the torrent file.
     - `<piece_index>`: The index of the piece to download.

   - **Example**:
     ```bash
     ./your_bittorrent.sh download_piece -o /tmp/torrents2844170027/piece-0 /tmp/torrents2844170027/codercat.gif.torrent 0
     ```
     
   - **Expected Output**:
     ```bash
     Downloaded piece_0 at path: /tmp/torrents2844170027/piece-0
     ```

#### `handshake`
   - **Description**: Performs a peer handshake using the specified torrent file.
   - **Parameters**:
     - `<torrent_file>`: The path to the torrent file.
     - `<peer_address>`: The socket address of the peer to connect to in the form of `ip`:`port`

   - **Example**:
     ```bash
     ./your_bittorrent.sh handshake /tmp/torrents768971451/test.torrent 127.0.0.1:38919
     ```

   - **Expected Output**:
     ```bash
     Peer ID: 9f07666979b5f02517d3edcb067abfd51a64ff6c
     ```

#### `peers`
   - **Description**: Retrieves a list of peers' addresses from the tracker specified in the torrent file.
   - **Parameters**:
     - `<torrent_file>`: The path to the torrent file.

   - **Example**:
     ```bash
     ./your_bittorrent.sh peers /tmp/torrents3086496673/test.torrent
     ```
     
   - **Expected Output**:
     ```bash
     Peers for test.torrent:
     
     188.119.61.177:6881
     185.107.13.235:54542
     88.99.2.101:6881
     ```


#### `info`
   - **Description**: Retrieves information from a torrent file, including the tracker URL, length, and piece hashes.
   - **Parameters**:
     - `<torrent_file>`: The path to the torrent file.
   
   - **Example**:
     ```bash
     ./your_bittorrent.sh info /tmp/torrents1294332965/test.torrent
     ```
     
   - **Expected Output**:
     ```
     Tracker URL: http://bttracker.debian.org:6969/announce
     Length: 1572864
     Info Hash: 753da4379d9a11139c55fecdba516f42dd9b1035
     Piece Length: 262144
     Piece Hashes:
     311c3f2436c1394acea2dafd2c812b7a3f4cd05a
     008c19a3468bef54e1a75e8b6a71d8529a1c0a6a
     912be9466cf461594129f6faf070a5aa6ca6b4d7
     f68259b74092c7a95965bdf0101f7a74110ca8f7
     d629b0e5245e67a3108598ef45f3be134d6837b7
     70edcac2611a8829ebf467a6849f5d8408d9d8f4
     ```

## Roadmap

- [ ] feat: Download from magnet links

---