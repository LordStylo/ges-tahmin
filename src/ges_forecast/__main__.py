from __future__ import annotations

import argparse
from pathlib import Path
from wsgiref.simple_server import make_server

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Yerel GES saatlik üretim tahmin arayüzü")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with make_server(args.host, args.port, create_app(args.data_dir)) as server:
        print(f"GES Tahmin arayüzü: http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
