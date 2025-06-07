import curses
import asyncio
import subprocess
import sys

import deepBle_discovery_tool as deep
import bleshellexploit
import bleak_stats
import replay_attack
from utility_scripts import check_bt_utilities as bt_util

MENU = [
    "Detailed Scan",
    "Vulnerability Test",
    "Session Stats",
    "Static Visualization",
    "MITM Proxy",
    "Replay Attack Test",
    "Exit"
]

def run_option(index, stdscr):
    if index == 0:
        asyncio.run(deep.run_detailed_scan())
    elif index == 1:
        stdscr.addstr(len(MENU)+2, 0, "Target address: ")
        curses.echo()
        addr = stdscr.getstr(len(MENU)+2, 16, 40).decode()
        curses.noecho()
        results = bleshellexploit.run_exploit(addr)
        stdscr.addstr(len(MENU)+3, 0, str(results))
        stdscr.getch()
    elif index == 2:
        subprocess.run([sys.executable, "bleak_stats.py"])
    elif index == 3:
        bt_util.visualize_results(live=False)
    elif index == 4:
        stdscr.addstr(len(MENU)+2, 0, "Target address: ")
        curses.echo()
        addr = stdscr.getstr(len(MENU)+2, 16, 40).decode()
        curses.noecho()
        if sys.platform.startswith('win'):
            subprocess.run([sys.executable, "win_mitm.py", addr])
        elif sys.platform.startswith('darwin'):
            subprocess.run([sys.executable, "mac_mitm.py", addr])
        else:
            stdscr.addstr(len(MENU)+3, 0, "MITM not supported on this OS")
            stdscr.getch()
    elif index == 5:
        stdscr.addstr(len(MENU)+2, 0, "Target address: ")
        curses.echo()
        addr = stdscr.getstr(len(MENU)+2, 16, 40).decode()
        curses.noecho()
        asyncio.run(replay_attack.automatic_replay_test(addr))
    elif index == 6:
        raise SystemExit


def main(stdscr):
    curses.curs_set(0)
    pos = 0
    while True:
        stdscr.clear()
        for i, item in enumerate(MENU):
            mode = curses.A_REVERSE if i == pos else curses.A_NORMAL
            stdscr.addstr(i, 0, item, mode)
        key = stdscr.getch()
        if key == curses.KEY_UP:
            pos = (pos - 1) % len(MENU)
        elif key == curses.KEY_DOWN:
            pos = (pos + 1) % len(MENU)
        elif key in (curses.KEY_ENTER, ord('\n')):
            run_option(pos, stdscr)
        stdscr.refresh()

if __name__ == '__main__':
    curses.wrapper(main)
