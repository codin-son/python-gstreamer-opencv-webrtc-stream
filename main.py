import argparse
import asyncio
import json
import os
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import cv2
import queue
import threading

# Custom video capture class that reads frames in a separate thread
class CustomVideoCapture:
    def __init__(self, name):
        # Initialize video capture (camera or RTSP stream)
        self.cap = cv2.VideoCapture(name)
        self.q = queue.Queue(maxsize=1)  # Queue to store latest frame
        self.stopped = False
        # Start background thread to continuously read frames
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    def _reader(self):
        # Background thread that continuously reads frames
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                self.stopped = True
                break
            # Keep only the latest frame in queue
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        # Get the latest frame from queue
        return self.q.get()

    def release(self):
        # Stop capture and cleanup resources
        self.stopped = True
        self.cap.release()
        if self.t.is_alive():
            self.t.join(timeout=1.0)
        print("CustomVideoCapture released")

# WebRTC video track that streams captured frames
class VideoTrack(VideoStreamTrack):
    def __init__(self, video_capture):
        super().__init__()
        self.video_capture = video_capture
        self.running = True

    async def recv(self):
        # Called by WebRTC to get next video frame
        if not self.running:
            raise RuntimeError("Track stopped")
        
        # Get timestamp for frame
        pts, time_base = await self.next_timestamp()
        frame = self.video_capture.read()
        
        if frame is None:
            self.running = False
            raise RuntimeError("No frame available")
        
        # Convert OpenCV frame to WebRTC VideoFrame
        frame = VideoFrame.from_ndarray(frame, format="bgr24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self):
        # Stop the video track
        self.running = False
        print("VideoTrack stopped")

# Main WebRTC server class
class WebRTCServer:
    def __init__(self):
        self.ROOT = os.path.dirname(__file__)
        try:
            # Initialize video capture from RTSP stream
            self.video_capture = CustomVideoCapture(
                "rtspsrc location=\"rtsp://192.168.1.121:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream\" latency=0 ! decodebin ! videoconvert ! video/x-raw,format=BGR ! appsink"
            )
            # Alternative: use webcam (commented out)
            # self.video_capture = CustomVideoCapture(0)
        except Exception as e:
            print(f"Failed to initialize video capture: {e}")
            raise
        # Keep track of active peer connections
        self.pcs = set()

    async def offer(self, request):
        # Handle WebRTC offer from client
        try:
            # Handle CORS preflight request
            if request.method == "OPTIONS":
                return web.Response(
                    status=200,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                    }
                )

            # Parse client's offer
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            
            # Create video track and peer connection
            video_track = VideoTrack(self.video_capture)
            pc = RTCPeerConnection()
            self.pcs.add(pc)
            
            # Add video track to peer connection
            pc.addTrack(video_track)

            # Handle connection state changes
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                if pc.connectionState in ["failed", "disconnected", "closed"]:
                    await pc.close()
                    self.pcs.discard(pc)

            # Handle ICE connection state changes
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                if pc.iceConnectionState in ["disconnected", "failed", "closed"]:
                    await pc.close()
                    self.pcs.discard(pc)

            # Set remote description and create answer
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Return answer to client
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                ),
                headers={"Access-Control-Allow-Origin": "*"}
            )
        except Exception as e:
            return web.Response(
                status=500,
                text=f"Error processing offer: {str(e)}",
                headers={"Access-Control-Allow-Origin": "*"}
            )

    async def on_shutdown(self, app):
        # Clean up when server shuts down
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()
        self.video_capture.release()

    def create_app(self, cors="*"):
        # Create web application with routes and middleware
        app = web.Application()
        app.on_shutdown.append(self.on_shutdown)
    
        # CORS middleware to handle cross-origin requests
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == "OPTIONS":
                return web.Response(
                    status=200,
                    headers={
                        "Access-Control-Allow-Origin": cors,
                        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                    }
                )
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = cors
            return response
    
        # Simple root handler
        async def root_handler(request):
            return web.Response(text="WebRTC Server is running")
    
        # Add middleware and routes
        app.middlewares.append(cors_middleware)
        app.router.add_post("/offer", self.offer)  # WebRTC offer endpoint
        app.router.add_get("/", root_handler)      # Root endpoint
         
        return app

# Main entry point
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WebRTC video stream server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server")
    parser.add_argument("--port", type=int, default=9922, help="Port for HTTP server")
    parser.add_argument("--cors", default="*", help="CORS origin")
    args = parser.parse_args()
    
    # Create and run server
    server = WebRTCServer()
    app = server.create_app(cors=args.cors)
    web.run_app(app, host=args.host, port=args.port)