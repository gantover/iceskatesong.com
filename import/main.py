"""Import service. A stub for now: it starts and idles until a later issue gives it work."""

import signal
import sys


def main() -> None:
    # As PID 1 the default SIGTERM handler is ignored, so exit explicitly on `docker compose stop`.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print("import: idle", flush=True)
    signal.pause()


if __name__ == "__main__":
    main()
