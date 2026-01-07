from flask import Flask, Response, render_template, send_from_directory
import cv2
import time
import subprocess
import threading
import os
import psutil

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
RTSP_URL = "rtsp://192.168.2.224:554/stream1?tcp"
RECORD_DIR = "/home/admin/cam_frames/recordings"

# Ensure recordings folder exists
os.makedirs(RECORD_DIR, exist_ok=True)


# -----------------------------
# KILL FFMPEG IF NEEDED
# -----------------------------
def kill_ffmpeg():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and "ffmpeg" in proc.info['name']:
            try:
                proc.kill()
            except:
                pass


# -----------------------------
# START FFMPEG RECORDING
# -----------------------------
def start_ffmpeg_recording():
    output_pattern = os.path.join(RECORD_DIR, "recording_%Y-%m-%d_%H-%M-%S.mp4")

    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", "1800",        # 30 minutes
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        "-strftime", "1",
        output_pattern
    ]

    subprocess.Popen(cmd)  # Run in background


# -----------------------------
# WATCHDOG — DETECT FILE DELETION
# -----------------------------
def recording_watchdog():
    while True:
        time.sleep(5)

        files = sorted(os.listdir(RECORD_DIR))
        if not files:
            continue

        newest = files[-1]
        full_path = os.path.join(RECORD_DIR, newest)

        # If the newest file was deleted → restart FFmpeg
        if not os.path.exists(full_path):
            print("⚠️ Recording deleted — restarting FFmpeg...")
            kill_ffmpeg()
            time.sleep(1)
            start_ffmpeg_recording()


# -----------------------------
# CAMERA STREAMING
# -----------------------------
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


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video")
def video():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/recordings")
def recordings():
    files = sorted(os.listdir(RECORD_DIR))
    file_links = [f"<a href='/download/{f}'>{f}</a>" for f in files]
    return "<br>".join(file_links)


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(RECORD_DIR, filename, as_attachment=True)

@app.route("/start_recording")
def start_recording():
    kill_ffmpeg()
    start_ffmpeg_recording()
    return "Recording started"

@app.route("/stop_recording")
def stop_recording():
    kill_ffmpeg()
    return "Recording stopped"

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    threading.Thread(target=start_ffmpeg_recording, daemon=True).start()
    threading.Thread(target=recording_watchdog, daemon=True).start()

    app.run(host="0.0.0.0", port=5051, threaded=True)
