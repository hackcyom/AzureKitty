import subprocess
import time

import timeout_decorator

from .utils import *


class SessionPS:
    def __init__(self, debug) -> None:
        self.sess = None
        self.assert_handler = AssertHandler()
        self.debug = debug
        # 
        self.infos = {}

    def __str__(self) -> None:
        print(f"Session PowerShell")

    def create_session(self) -> bool:
        """
        This function will connect to the Microsoft account

        Return:
                - bool
        """
        # Check if we are on Windows or MacOS
        if platform.system() == "Windows":
            sub_process = subprocess.Popen(
                ["powershell.exe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
        else:
            sub_process = subprocess.Popen(
                ["pwsh"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )

        sub_process.stdin.write("Connect-ExchangeOnline\n".encode("utf-8"))
        sub_process.stdin.flush()

        # check if we are connected to ExchangeOnline successfully
        if not self.assert_handler.handle_assert(
            b"This V3 EXO PowerShell"
            in read_until(
                sub_process,
                b"----------------------------------------------------------------------------------------\r\n\n",
            ),
            "An error occured while creating the session for PowerShell. Couldn't find the success message. Maybe check your internet connection?",
        ):
            return False

        sub_process.stdin.write(
            "Connect-MicrosoftTeams | ft -HideTableHeaders\n".encode("utf-8")
        )
        sub_process.stdin.flush()


        sub_process.stdin.write(
            "Import-Module ExchangeOnlineManagement, MicrosoftTeams, Microsoft.Online.SharePoint.PowerShell, Az, AzureAD\n".encode("utf-8")
        )
        sub_process.stdin.flush()

        # check if we are connected to MicrosoftTeams successfully
        if not self.assert_handler.handle_assert(
            b"AzureCloud" in read_until(sub_process, b"\n\n"),
            "An error occured while creating the session for PowerShell. Couldn't find the success message. Maybe check your internet connection?",
        ):
            return False

        self.sess = sub_process
        return True

    def check_session(self) -> bool:
        """
        This function will return True if the PS session is still open

        Return:
                - bool
        """
        self.sess.stdin.write("echo 'AzureKitty check'\n".encode("utf-8"))
        self.sess.stdin.flush()

        success_message = b"AzureKitty check\n"
        response = read_until(self.sess, success_message)

        if not self.assert_handler.handle_assert(
            success_message in response,
            "An error occurred while verifying the session for PowerShell. Couldn't find the success message. Maybe the subprocess was killed?",
        ):
            return False

        return True

    def run_cmd(self, cmd: str) -> bytes:
        """
        Run a command in PowerShell. The command is between a 'AZUREKITTY_START' and 'AZUREKITTY_END'
        for ease of parsing.
        The return value is ONLY the result of the command

        Return:
                - bytes: result of the command(s)
        """
        start = "AZUREKITTY_START"
        end = "AZUREKITTY_END"
        command = f"echo {start}; {cmd}; echo {end}\n".encode("utf-8")

        self.sess.stdin.write(command)
        self.sess.stdin.flush()
        self.sess.stdout.readline()

        result = read_until(self.sess, end.encode())

        if self.debug:
            info(f"Command Result: {result}")

        parsed_result = result.split(start.encode(), 1)[-1].split(end.encode(), 1)[0][1:]

        return parsed_result

    def ret_session(self) -> subprocess.Popen:
        return self.sess


class PSAudit:
    def __init__(self, session: SessionPS, debug: bool) -> None:
        self.session = session
        self.assert_handler = AssertHandler()
        self.debug = debug

    def ret_session(self) -> subprocess.Popen:
        return self.session.ret_session()

    @timeout_decorator.timeout(30)
    def pwsh_run(self, cmd: str) -> bytes:
        """
        This function launches a PowerShell command and returns the output
        """
        if self.debug:
            info(f"Running command: {cmd}")

        result = self.session.run_cmd(cmd)

        if result is None:
            raise Exception("Command execution failed or timed out.")

        return result
