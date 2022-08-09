#!/usr/bin/env python3
"""
A reference spartan:// protocol server.

Copyright (c) Michael Lazar
Blue Oak Model License 1.0.0
"""
import argparse
from datetime import datetime
import mimetypes
import os
import pathlib
import shutil
from socketserver import ThreadingTCPServer, StreamRequestHandler
from urllib.parse import unquote


class SpartanRequestHandler(StreamRequestHandler):
    def handle(self):
        try:
            self._handle()
        except ValueError as e:
            self.write_status(4, e)
        except Exception:
            self.write_status(5, "An unexpected error has occurred")
            raise

    def _handle(self):
        request = self.rfile.readline(4096)
        request = request.decode("ascii").strip("\r\n")
        print(f'{datetime.now().isoformat()} "{request}"')

        hostname, path, content_length = request.split(" ")
        if not path:
            raise ValueError("Not Found")

        path = unquote(path)

        # Guard against breaking out of the directory
        safe_path = os.path.normpath(path.strip("/"))
        if safe_path.startswith(("..", "/")):
            raise ValueError("Not Found")

        filepath = root / safe_path
        if filepath.is_file():
            self.write_file(filepath)
        elif filepath.is_dir():
            if not path.endswith("/"):
                # Redirect to canonical path with trailing slash
                self.write_status(3, f"{path}/")
            elif (filepath / "index.gmi").is_file():
                self.write_file(filepath / "index.gmi")
            else:
                self.write_status(2, "text/gemini")
                self.write_line("=>..")
                for child in filepath.iterdir():
                    if child.is_dir():
                        self.write_line(f"=>{child.name}/")
                    else:
                        self.write_line(f"=>{child.name}")
        else:
            raise ValueError("Not Found")

    def write_file(self, filepath):
        mimetype, encoding = mimetypes.guess_type(filepath, strict=False)
        mimetype = mimetype or "application/octet-stream"
        with filepath.open("rb") as fp:
            self.write_status(2, mimetype)
            shutil.copyfileobj(fp, self.wfile)

    def write_line(self, text):
        self.wfile.write(f"{text}\n".encode("utf-8"))

    def write_status(self, code, meta):
        self.wfile.write(f"{code} {meta}\r\n".encode("ascii"))


mimetypes.add_type("text/gemini", ".gmi")

parser = argparse.ArgumentParser(description="A spartan static file server")
parser.add_argument("dir", default=".", nargs="?", type=pathlib.Path)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default=3000, type=int)
args = parser.parse_args()

root = args.dir.resolve(strict=True)
print(f"Root Directory {root}")

server = ThreadingTCPServer((args.host, args.port), SpartanRequestHandler)
print(f"Listening on {server.server_address}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
