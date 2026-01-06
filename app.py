from flask import Flask, Response, render_template
import cv2
import time

app = Flask(__name__)

RTSP_URL = "rtsp://192.168.2.224:554/stream1?tcp"

def get_cam():
    return cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

def generate_frames():
    while True:
        cam = get_cam()

        if not cam.isOpened():
            print("❌ Cannot open RTSP stream — retrying...")
            time.sleep(1)
            continue

        print("📡 Stream: Connected")

        while True:
            ret, frame = cam.read()
            if not ret:
                print("⚠️ Stream: Frame failed — reconnecting...")
                break

            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame_bytes +
                b"\r\n"
            )

        cam.release()
        time.sleep(0.2)

@app.route("/video")
def video():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051, threaded=True)
