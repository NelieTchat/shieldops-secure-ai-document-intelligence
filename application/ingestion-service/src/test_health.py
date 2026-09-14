from health import start_health_server
import time

start_health_server()

print("Health server started. Try visiting http://localhost:8080/health in your browser,")
print("or open a second terminal and run: curl http://localhost:8080/health")
print("Press Ctrl+C to stop.")

while True:
    time.sleep(1)
