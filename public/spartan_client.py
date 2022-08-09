#!/usr/bin/env python3
"""
A reference spartan:// protocol client.

Copyright (c) Michael Lazar
Blue Oak Model License 1.0.0
"""
import argparse
import shutil
import socket
import sys
from urllib.parse import urlparse, unquote_to_bytes, quote_from_bytes


def fetch_url(url, infile=None):
    url_parts = urlparse(url)
    if url_parts.scheme != "spartan":
        raise ValueError("Unrecognized URL scheme")

    host = url_parts.hostname
    port = url_parts.port or 300
    path = url_parts.path or "/"
    query = url_parts.query

    redirect_url = None

    with socket.create_connection((host, port)) as sock:
        if infile:
            data = infile.read()
        elif query:
            data = unquote_to_bytes(query)
        else:
            data = b""

        encoded_host = host.encode("idna")
        encoded_path = quote_from_bytes(unquote_to_bytes(path)).encode("ascii")
        sock.send(b"%s %s %d\r\n" % (encoded_host, encoded_path, len(data)))
        sock.send(data)

        fp = sock.makefile("rb")
        response = fp.readline(4096).decode("ascii").strip("\r\n")
        print(response, file=sys.stderr, flush=True)

        parts = response.split(" ", maxsplit=1)
        code, meta = int(parts[0]), parts[1]
        if code == 2:
            shutil.copyfileobj(fp, sys.stdout.buffer)
        elif code == 3:
            redirect_url = url_parts._replace(path=meta).geturl()

    if redirect_url:
        fetch_url(redirect_url)


parser = argparse.ArgumentParser(description="A spartan client")
parser.add_argument("url")
parser.add_argument("--infile", type=argparse.FileType("rb"))
args = parser.parse_args()

try:
    fetch_url(args.url, args.infile)
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
except KeyboardInterrupt:
    pass
