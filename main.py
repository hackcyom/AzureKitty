import argparse
import asyncio
import re
import platform
from dataclasses import dataclass

from scans import *


def scanner(scan, psaudit, mcaudit, azaudit) -> dict:
    """This function runs the command of the scan and returns the output

    Args:
            scan (dict): Dictionary containing the command to be run
            psaudit (object): Powershell audit object
            mcaudit (object): Microsoft graph audit object
            azaudit (object): Azure audit object

    Returns:
            dict: Returns the output of the scan
    """
    match scan["type"]:
        case "ps":  # if its powershell command
            output = psaudit.pwsh_run(scan["command"])
        case "az":  # if its azure command
            ### Runs the command and if it fails then it's not applicable and adds the reason in the comment key of the scan dict
            try:
                output = azaudit.az_run(scan["command"])
            except Exception as e:
                scan["comment"] = str(e)
                output = None
        case _:
            raise Exception()
    return output


def get_result(output, scan, secure_score):
    if "Error" == scan.get("status", None):
        print_audit_element(scan["id"], scan["name"], scan["status"])
        return scan

    scan_type = scan.get("type")
    check = scan.get("check")
    applies_if_empty = scan.get("applies_if_empty")

    match scan_type:
        case "ps":
            if b"is not recognized as a name of a cmdlet" in output:
                term = output.split(b"The term ")[1].split(
                    b"\x1b[0m\n\x1b[31;1m\x1b[31;1mCheck the spelling of the name"
                )[0]
                warning(term.decode())
                scan["status"] = "Error"
            else:
                scan["status"] = str(re.search(check, output.decode()) is not None)

        case "az":
            if output is None or (not output and applies_if_empty == "False"):
                scan["status"] = "NotApplicable"
            elif check == "None":
                scan["status"] = "True"
            elif check == "":
                scan["status"] = "False"
            else:
                if isinstance(output, list):
                    valid_entries = sum(
                        1
                        for entry in output
                        if entry is not None and check in str(entry)
                    )
                    scan["status"] = str(len(output) == valid_entries)
                else:
                    if check.startswith("regex"):
                        reg = re.compile(" ".join(check.split()[1:]))
                        scan["status"] = str(len(reg.findall(output)) != 0)
                    else:
                        scan["status"] = str(check in str(output))

        case "mc":
            info(f"Secure Score: {secure_score}")
            return scan

        case _:
            raise Exception("Invalid scan type")

    print_audit_element(scan["id"], scan["name"], scan["status"])
    return scan


async def main():
    args = parse_args()
    if args is None:
        return -1

    info("Starting AzureKitty, connecting... This may take some time. Be patient.")

    if not platform.machine() in ("AMD64", "x86_64"):
        warning(
            "Some check may not work on this architecture. AzureAD module requires Amd64 architecture. The check will still be run, but they will likely say that the module is not found."
            )

    assert_handler = AssertHandler()
    sess_ps = SessionPS(args.debug)
    sess_az = SessionAZ(args.debug)
    sess_mc = SessionMC(args.debug)

    ### POWERSHELL ###
    if not assert_handler.handle_assert(
        True == sess_ps.create_session(),
        "An error occured while creating the PowerShell session. The create_session() function did not return True.",
    ):
        return -1
    success(f"Connected successfully to Microsoft.")

    if not assert_handler.handle_assert(
        True == sess_ps.check_session(),
        "An error occured while verifying the PowerShell session. The check_session() function did not return True.",
    ):
        return -1
    success(f"Session checked successfully.")

    ### AZURE ###
    if not assert_handler.handle_assert(
        True == sess_az.create_session(),
        "An error occured while creating the Azure session. The create_session() function did not return True.",
    ):
        return -1
    success(f"Connected successfully to Azure.")

    if not assert_handler.handle_assert(
        True == sess_az.check_session(),
        "An error occured while verifying the Azure session. The check_session() function did not return True.",
    ):
        return -1
    success(f"Session checked successfully.")

    azaudit = AZAudit(sess_az, args.debug)
    psaudit = PSAudit(sess_ps, args.debug)
    mcaudit = MCAudit(sess_mc, args.debug)


    objects = ObjectParser(args.input, args.debug).parse()
    for obj in objects:
        obj["comment"] = ""

    for scan in objects:
        try:
            output = scanner(scan, psaudit, mcaudit, azaudit)
        except Exception as e:
            if args.debug:
                error(e)
            scan["status"] = "Error"
            output = ""
        scan = get_result(output, scan, None)

    success(f"Fully scanned the Azure/Office365 configuration.")

    if args.output:
        cleaned_result = {
            key: result[key] for key in ["id", "name", "status", "comment"]
        }
        ObjectSerializer(cleaned_result, args.output, args.debug).serialize()
        success(f"Results written to {args.output}.")


if __name__ == "__main__":
    asyncio.run(main())
