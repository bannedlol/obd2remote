import signal
import sys
import time

from ingestor import MQTTInfluxIngestor


def main():
    ingestor = MQTTInfluxIngestor()
    ingestor.start()

    # Graceful shutdown on SIGINT/SIGTERM
    def _shutdown(signum, frame):
        ingestor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Block forever
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
