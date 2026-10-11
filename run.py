"""SwiftLogic catalogue price watcher — local demo launcher.

Binds 127.0.0.1 and picks a free port so Windows does not raise WinError 10013
when 8000 is reserved or already taken.
"""
import socket
import uvicorn


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


if __name__ == "__main__":
    port = free_port()
    print(f"SwiftLogic price scraper → http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
