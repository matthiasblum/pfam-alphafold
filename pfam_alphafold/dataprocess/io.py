from datetime import datetime
from sys import stderr


def log(message: str):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{message}", file=stderr)
