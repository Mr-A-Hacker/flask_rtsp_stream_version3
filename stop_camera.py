import subprocess

service_name = "camera.service"

print("Stopping camera service...")

subprocess.run(["sudo", "systemctl", "stop", service_name])

print("Camera service stopped.")
