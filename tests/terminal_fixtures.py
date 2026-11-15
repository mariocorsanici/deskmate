"""External terminal/process doubles for tests that target routing, not startup."""
TTY_REPLY = "print('/dev/ttys042\\tTEST-TERMINAL')\n"


def ps_stub(directory):
    return ("import sys\n"
            "if '-t' in sys.argv:\n"
            "    print('4242 ' + " + repr(str(directory / 'claude')) + ")\n"
            "    print('4243 ' + " + repr(str(directory / 'codex')) + ")\n")


def terminal_stub():
    # Consume only the payload named by this command, never scan shared temp.
    return ("import shlex,sys\nfrom pathlib import Path\n"
            "sys.stdin.read()\n"
            "parts=shlex.split(sys.argv[2])\n"
            "if '-c' in parts: parts=shlex.split(parts[parts.index('-c')+1])\n"
            "if '--payload' in parts:\n"
            "    path=Path(parts[parts.index('--payload')+1])\n"
            "    path.unlink()\n"
            "    path.parent.rmdir()\n" + TTY_REPLY)
