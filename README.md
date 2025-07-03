# WebRTC Video Stream Server

This project implements a WebRTC server for streaming video from an RTSP source (or webcam) using Python, `aiortc`, and OpenCV with GStreamer support. The server handles WebRTC peer connections and streams video frames to connected clients.

## Prerequisites

- **Operating System**: Ubuntu 20.04 (recommended for compatibility with GStreamer and OpenCV)
- **Python Version**: 3.10
- **Package Manager**: `uv` (recommended for managing Python dependencies)
- **OpenCV**: Custom-built with GStreamer support enabled
- **GStreamer**: Required for handling RTSP streams

## Setup Instructions

### 1. Install System Dependencies

Ensure you have the necessary system packages installed for GStreamer and OpenCV:

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-dev python3-pip \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav libopencv-dev
```

### 2. Install `uv`

Install `uv`, a fast Python package manager, if not already installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Set Up Python Environment

Create and activate a virtual environment using `uv`:

```bash
uv venv
source .venv/bin/activate
```

### 4. Install Python Dependencies

Install the required Python packages using `uv`:

```bash
uv sync
```

Ensure a `pyproject.toml` file exists with the following dependencies:

```toml
[project]
dependencies = [
    "aiohttp",
    "aiortc",
    "av"
]
```

### 5. Build OpenCV with GStreamer Support (or use provided opencv)

To enable GStreamer support in OpenCV, build OpenCV from source using the `opencv-python` repository:

1. Clone the `opencv-python` repository:

```bash
git clone --recursive https://github.com/skvark/opencv-python.git
cd opencv-python
```

2. Set the CMake argument to enable GStreamer:

```bash
export CMAKE_ARGS="-DWITH_GSTREAMER=ON"
```

3. Upgrade `pip` and install `wheel`:

```bash
pip install --upgrade pip wheel
```

4. Build the OpenCV wheel (this may take 5 minutes to over 2 hours depending on your hardware):

```bash
pip wheel . --verbose
```

5. Install the generated wheel (it may be in the `dist/` directory):

```bash
uv add opencv_python*.whl
```

6. Verify OpenCV installation with GStreamer support:

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer
```

Look for `GStreamer: YES` in the output.

### 6. Run the Server

Run the WebRTC server with the following command:

```bash
uv run python server.py --host 0.0.0.0 --port 9922
```

- `--host`: Specifies the host IP (default: `0.0.0.0`)
- `--port`: Specifies the port (default: `9922`)
- `--cors`: Specifies CORS origin (default: `*`)

The server will start and listen for WebRTC offer requests at `http://<host>:9922/offer`.

## Usage

1. **RTSP Source**: The server is configured to stream from an RTSP source by default. Modify the `CustomVideoCapture` initialization in `server.py` to use a different RTSP URL or switch to a webcam by uncommenting the line `self.video_capture = CustomVideoCapture(0)`.

   Example RTSP URL in the code:

   ```python
   CustomVideoCapture(
       "rtspsrc location=\"rtsp://192.168.1.121:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream\" latency=0 ! decodebin ! videoconvert ! video/x-raw,format=BGR ! appsink"
   )
   ```

2. **Client Connection**: Connect a WebRTC client (e.g., a browser-based WebRTC application) to the server by sending an SDP offer to `http://<host>:9922/offer`. The server will respond with an SDP answer.

3. **Access Root Endpoint**: Check if the server is running by accessing `http://<host>:9922/` in a browser, which should return "WebRTC Server is running".

## Flowchart

Below is a flowchart illustrating the high-level workflow of the WebRTC video stream server:

![alt text](chart.svg)

## Notes

- Ensure the RTSP source is accessible and the credentials (if any) are correct.
- The server supports CORS for cross-origin requests, configurable via the `--cors` argument.
- If you encounter issues with video capture, verify that GStreamer is correctly installed and the pipeline is valid.
- For debugging, check the console output for errors related to video capture or WebRTC connection states.

## Troubleshooting

- **GStreamer Errors**: Ensure all GStreamer plugins are installed (`gstreamer1.0-plugins-*`). Test the RTSP pipeline using `gst-launch-1.0`:

  ```bash
  gst-launch-1.0 rtspsrc location="rtsp://192.168.1.121:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream" ! decodebin ! videoconvert ! autovideosink
  ```

- **OpenCV Import Errors**: Verify that OpenCV is built with GStreamer support and linked to the correct Python version.
- **WebRTC Connection Issues**: Ensure the client sends a valid SDP offer and that the network allows WebRTC traffic (ICE candidates, STUN/TURN if needed).

## License

This project is licensed under the MIT License.