import os
import select
import sys
import time
import tty

PASTE_LENGTH = 20
ANSWER_SECONDS = 5

tty.setraw(0)


def out(text: str) -> None:
    os.write(1, text.encode())


def answers() -> bool:
    out("\x1b[>4;?m\x1b[?u\x1b]11;?\x1b\\\x1b[6n\x1b[c")
    heard = b""
    deadline = time.time() + ANSWER_SECONDS
    while time.time() < deadline and not (b"R" in heard and heard.endswith(b"c")):
        ready, _, _ = select.select([0], [], [], 0.1)
        if ready:
            heard += os.read(0, 256)
    return b"R" in heard and heard.endswith(b"c")


if not answers():
    out("The terminal never answered.\r\n")
    sys.exit(3)
out("Browser\x1b[1Cdidn't\x1b[1Copen?\x1b[1CUse\x1b[1Cthe\x1b[1CURL\x1b[1Cbelow\r\n")
out("https://example.test/oauth?code=true&state=abc\r\n")
out("Paste\x1b[1Ccode\x1b[1Chere\x1b[1Cif\x1b[1Cprompted\r\n╭────╮\r\n│ │\r\n╰────╯\r\n")
typed = ""
while True:
    chunk = os.read(0, 4096).decode()
    if chunk == "\r" and typed:
        break
    if len(chunk) > PASTE_LENGTH:
        typed += chunk.replace("\r", "").replace("\n", "")
        out("\x1b[2K\r" + "*" * len(typed))
        continue
    typed += chunk.split("\r")[0]
    if "\r" in chunk and typed:
        break
out(f"\r\nYour\x1b[1Ctoken:\r\nsk-ant-oat01-{typed.replace('#', '_')}\r\n")
time.sleep(5)
