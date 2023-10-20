import time

import timeout_decorator
from azure.cli.core import get_default_cli
from azure.identity import InteractiveBrowserCredential

from .utils import *


class SessionAZ:
    def __init__(self, debug: bool) -> None:
        self.sess = None
        self.assert_handler = AssertHandler()
        self.infos = {}
        self.debug = debug

    def __str__(self) -> None:
        print(f"Session Azure")

    def create_session(self) -> bool:
        """This function will connect to the Microsoft account.

        Returns:
                bool: True if the session was created successfully
        """
        self.creds = InteractiveBrowserCredential()

        def fetch_info(info_key, command, error_message, info_name):
            result = self.run_cmd(command)
            if not self.assert_handler.handle_assert(
                result is not False, error_message
            ):
                return False

            self.infos[info_key] = result
            if self.infos[info_key] is not None:
                success(f"Successfully fetched the {info_name}:")
                for account in self.infos[info_key]:
                    success(f"\t{account[0]} - {account[1]}")
            else:
                warning(f"No {info_name} were found")
            return True

        if not fetch_info(
            "<subscriptionid>",
            "account get-access-token",
            "An error occurred while fetching the subscription ID and access token for the current Azure subscription.",
            "subscription ID and access token",
        ):
            return False

        code = self.run_cmd("login")
        if not self.assert_handler.handle_assert(
            code is not False, "An error occurred while creating the session for Azure."
        ):
            return False
        success(f"Running on {code[0]['name']} as user {code[0]['user']['name']}")

        infos_to_fetch = {
            "<storage_accounts>": [
                "storage account list --query [*].[name,resourceGroup]",
                "An error occurred while fetching the storage accounts for the current Azure subscription.",
                "storage accounts",
            ],
            "<postgres_servers>": [
                "postgres server list --query [*].[name,resourceGroup]",
                "An error occurred while fetching the PostgreSQL Servers for the current Azure subscription.",
                "PostgreSQL servers",
            ],
            "<azure_sql_servers>": [
                "sql server list --query [*].[name,resourceGroup]",
                "An error occurred while fetching the Azure SQL Servers for the current Azure subscription.",
                "Azure SQL servers",
            ],
        }

        for info_key, info_values in infos_to_fetch.items():
            if not fetch_info(info_key, info_values[0], info_values[1], info_values[2]):
                return False

        return True

    def check_session(self) -> bool:
        """This function will return True if the AZ session is still open."""
        code = self.run_cmd("account show")

        if self.debug:
            info(f"az account show: {code}")

        return self.assert_handler.handle_assert(
            code is not False, "An error occurred while checking the session for Azure."
        )

    def run_cmd(self, cmd: str) -> str:
        """This function will run the command in the AZ CLI.

        Args:
                cmd (str): The command to run

        Returns:
                str: the result of the command
        """
        args = "-o none --only-show-errors"
        cmds = cmd.split() + args.split()
        cli = get_default_cli()

        cli.invoke(cmds)

        if self.debug:
            info(f"run_cmd result: {cli.result.result}")

        if cli.result.result:
            return cli.result.result

        return None


class AZAudit:
    def __init__(self, session: SessionAZ, debug: bool) -> None:
        self.assert_handler = AssertHandler()
        self.debug = debug
        self.session = session

    def batch_run(self, args: str, keywords: list, substitutes: list) -> list:
        """
        This function will take a command, and run it multiple times against a list of keywords to substitute with multiple names and resource groups that are present.
        Args:
                args - the command that will be run
                keywords - the keywords that will be replaced
                substitutes - the words that will replace the keywords
        Returns:
                list - a list of all the command outputs.
        """
        results = []

        if substitutes is None:
            raise Exception(f"No {keywords[0][1:-1]} were found")

        for name, resource_group in substitutes:
            args = args.replace(keywords[0], name)
            args = args.replace(keywords[1], resource_group)

            result = self.session.run_cmd(args)
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)

        return results

    @timeout_decorator.timeout(30)
    def az_run(self, args: str) -> list:
        """This function launches an Azure command and returns the output.
        It will also replace the arguments with the values from the session.

        Args:
                args (str): The command to run

        Returns:
                list: The result of the command
        """
        # Replace arguments with values from the session
        for attr, value in self.session.infos.items():
            args = args.replace(attr, value)

        replaceable_elems = [
            (
                self.session.infos["<storage_accounts>"],
                ["<storage_account_name>", "<storage_resource_group>"],
            ),
            (
                self.session.infos["<postgres_servers>"],
                ["<postgres_server_name>", "<postgres_resource_group>"],
            ),
            (
                self.session.infos["<azure_sql_servers>"],
                ["<azure_sql_server_name>", "<azure_sql_resource_group>"],
            ),
        ]

        for substitutes, keywords in replaceable_elems:
            for keyword in keywords:
                if keyword in args:
                    return self.batch_run(args, keywords, substitutes)

        if self.debug:
            info(f"Running command: {args}")

        result = self.session.run_cmd(args)
        return result
