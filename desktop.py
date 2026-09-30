"""Windows executable launcher."""
import os
import threading
import urllib.request
import webbrowser


def open_when_ready(url):
    for _ in range(120):
        try:
            with urllib.request.urlopen(url + "/api/status", timeout=1) as response:
                if response.status == 200:
                    if os.environ.get("PASTEHAPPY_NO_OPEN") != "1":
                        webbrowser.open(url)
                    return
        except OSError:
            threading.Event().wait(0.5)
    print("Startup timed out. Check the errors above.", flush=True)


if __name__ == "__main__":
    import app as backend
    from waitress import serve
    url = f"http://127.0.0.1:{backend.config.port}"
    threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    print(f"PasteHappy: {url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
    try:
        serve(backend.app, host="127.0.0.1", port=backend.config.port, threads=8)
    except KeyboardInterrupt:
        pass
