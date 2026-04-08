from __future__ import annotations

try:
    from .main import app, main as _main
except ImportError:
    from main import app, main as _main


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    _main(host=host, port=port)


if __name__ == "__main__":
    main()
