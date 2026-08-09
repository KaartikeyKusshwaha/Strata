"""
Threaded TCP command bridge for Strata, run inside Blender.

bpy calls are NOT thread-safe, so incoming requests are queued and drained
on Blender's main thread via a bpy.app.timers callback (Determinism /
Testing Philosophy: this file is the actual bpy/no-bpy boundary in practice,
not just a documented rule). Each request blocks its handling thread until
the main-thread handler finishes and posts a result back through a
per-request threading.Event.

Wire protocol: one JSON object per line (newline-delimited JSON), matching
strata/blender_io.py on the other end:
    {"command": "<name>", "params": {...}}
    -> {"ok": true, "result": ...} | {"ok": false, "error": "..."}
"""
from __future__ import annotations

import json
import queue
import socket
import threading
import traceback

import bpy
from . import environment_handlers
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9877  # blender-mcp defaults to 9876 -- kept distinct so both can run side by side

_command_registry = {}
_request_queue: queue.Queue = queue.Queue()
_server_socket = None
_server_thread = None
_running = False


def register_command(name):
    """Decorator: exposes a function as a bridge command, e.g. `build_geometry`."""
    def deco(fn):
        _command_registry[name] = fn
        return fn
    return deco

_command_registry["build_clouds"] = environment_handlers.handle_build_clouds
_command_registry["build_atmosphere"] = environment_handlers.handle_build_atmosphere
_command_registry["build_sky"] = environment_handlers.handle_build_sky
_command_registry["build_sun"] = environment_handlers.handle_build_sun
_command_registry["build_water"] = environment_handlers.handle_build_water



def _handle_client(conn):
    with conn:
        buffer = b""
        while _running:
            try:
                chunk = conn.recv(65536)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    request = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    conn.sendall((json.dumps({"ok": False, "error": f"bad json: {exc}"}) + "\n").encode())
                    continue

                done = threading.Event()
                box = {}
                _request_queue.put((request, done, box))
                done.wait(timeout=120)
                response = box.get("response", {"ok": False, "error": "handler timed out"})
                try:
                    conn.sendall((json.dumps(response) + "\n").encode())
                except OSError:
                    return


def _server_loop():
    global _server_socket
    _server_socket.listen(5)
    while _running:
        try:
            conn, _addr = _server_socket.accept()
        except OSError:
            break
        threading.Thread(target=_handle_client, args=(conn,), daemon=True).start()


def _drain_queue():
    """Runs on Blender's main thread via bpy.app.timers -- safe to call bpy here."""
    if not _running:
        return None  # stop rescheduling
    try:
        request, done, box = _request_queue.get_nowait()
    except queue.Empty:
        return 0.05

    name = request.get("command")
    params = request.get("params", {})
    handler = _command_registry.get(name)
    if handler is None:
        # Error Handling: no silent fallback -- list what IS available.
        box["response"] = {"ok": False, "error": f"unknown command: {name}. Registered: {sorted(_command_registry)}"}
    else:
        try:
            result = handler(**params)
            box["response"] = {"ok": True, "result": result}
        except Exception:
            box["response"] = {"ok": False, "error": traceback.format_exc()}
    done.set()
    return 0.01


def start(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    global _server_socket, _server_thread, _running
    if _running:
        return
    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _server_socket.bind((host, port))
    _running = True
    _server_thread = threading.Thread(target=_server_loop, daemon=True)
    _server_thread.start()
    bpy.app.timers.register(_drain_queue, first_interval=0.1)
    print(f"[Strata] bridge listening on {host}:{port}")


def stop():
    global _server_socket, _running
    _running = False
    if _server_socket:
        _server_socket.close()
        _server_socket = None
    print("[Strata] bridge stopped")
