import uvicorn
import os
import sys
import multiprocessing
import time

# Ensure the current directory (project root) is in sys.path
sys.path.append(os.getcwd())

def run_main_app():
    print("Starting Main Backend on port 8000...")
    # Disable reload in production/docker to avoid lock conflicts
    use_reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=use_reload)

def run_parser_service():
    print("Starting Parser Service on port 8001...")
    # Disable reload in production/docker
    use_reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    uvicorn.run("parser.main:app", host="0.0.0.0", port=8001, reload=use_reload)

if __name__ == "__main__":
    # simple process manager
    p1 = multiprocessing.Process(target=run_main_app)
    p2 = multiprocessing.Process(target=run_parser_service)

    p1.start()
    p2.start()

    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        print("Stopping services...")
        p1.terminate()
        p2.terminate()
