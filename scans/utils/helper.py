import argparse
import platform
import subprocess
import time

import colorama as cr
import timeout_decorator
from colorama import Fore as fg
from colorama import Style as st


def read_until(subprocess_obj: subprocess.Popen, delimiter: str) -> bytes:
    """
    This function takes a subprocess.Popen and a delimiter and will readline() until the delimiter is found
    """
    output = bytearray()
    delimiter_bytes = delimiter.decode()

    while True:
        line = subprocess_obj.stdout.readline()
        output += line

        if delimiter in output:
            break

        if subprocess_obj.poll() is not None:
            raise Exception(f"Process ended unexpectedly: {subprocess_obj.returncode}")

    return output


def parse_args():
    """
    This function lets us initialize command line arguments
    """
    ap = argparse.ArgumentParser(
        prog="AzureKitty",
        description="Azure and Office 365 automated audit tool",
        epilog="Made by HKCM",
    )

    ap.add_argument(
        "-i",
        "--input",
        help="Input a CSV file containing the audit config",
        default="audit_csv/ps.csv",
    )
    ap.add_argument("-o", "--output", help="Output an XLSX file containing the results")
    ap.add_argument(
        "-d",
        "--debug",
        help="Makes the tool much more verbose",
        default=False,
        action="store_true",
    )

    args = ap.parse_args()

    return args


class AssertException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class AssertHandler:
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode

    def handle_assert(self, condition, message=None):
        if not condition:
            if self.debug_mode:
                print("AssertionError:")
                print(f"\tCondition: {condition}")
                print(f"\tMessage: {message}")

            if message is None:
                raise Exception()

            else:
                raise AssertException(message)

        return True


### Initialize colorama
cr.init()

"""
These helpers will print various infos on the terminal
	info -> print info (grey)
	success -> print success (green)
	warning -> print warning (orange)
	error -> print error (red)
"""
COLORS = {
    "INFO": fg.WHITE,
    "SUCCESS": fg.GREEN,
    "WARNING": fg.YELLOW,
    "ERROR": fg.RED,
    "RESET": fg.RESET,
}


def print_colored(content, color):
    print(f"{COLORS[color]}[{color}] {content}{COLORS['RESET']}")


def info(content):
    print_colored(content, "INFO")


def success(content):
    print_colored(content, "SUCCESS")


def warning(content):
    print_colored(content, "WARNING")


def error(content):
    print_colored(content, "ERROR")


def print_audit_element(audit_id: int, name: str, is_validated: str):
    """
    This helper prints audit elements with colors and emojis based on their validation status.

    Args:
            audit_id (int): The audit element's identifier.
            name (str): The audit element's name.
            is_validated (str): Either "True", "False", "Error", or "NotApplicable".
    """
    COLORS = {
        "True": fg.GREEN,
        "False": fg.RED,
        "Error": fg.YELLOW,
        "NotApplicable": fg.WHITE + st.DIM,
    }

    EMOJIS = {
        "True": "\u2705",
        "False": "\u26D4",
        "Error": "\u26A0\uFE0F",
        "NotApplicable": "\u274C",
    }

    color = COLORS.get(is_validated, fg.WHITE)
    emoji = EMOJIS.get(is_validated, "\u274C")
    ending = fg.RESET + st.RESET_ALL
    print(f"{color}[{emoji}] {audit_id} - {name}{ending}")
