import os
import time

import requests
import uvicorn


def test_local():
    # Start the server in a separate process
    import subprocess
    import threading

    def run_server():
        os.chdir("backend/app")
        uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give the server time to start
    time.sleep(5)

    try:
        # Test health endpoint
        response = requests.get("http://localhost:8080/health")
        print("Health check response:")
        print(response.json())

        # Test root endpoint
        response = requests.get("http://localhost:8080/")
        print("\nRoot endpoint response:")
        print(response.json())

    except Exception as e:
        print(f"Error testing server: {e}")
    finally:
        # Clean up (will be handled by the daemon thread)
        pass


if __name__ == "__main__":
    test_local()
