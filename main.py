import argparse
import re
import platform
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from scans import *


def scanner(scan, psaudit, mcaudit, azaudit, psaudit_lock, mcaudit_lock, azaudit_lock):
    """This function runs the command of the scan and returns the output

    Args:
            scan (dict): Dictionary containing the command to be run
            psaudit (object): Powershell audit object
            mcaudit (object): Microsoft graph audit object
            azaudit (object): Azure audit object

    Returns:
            dict: Returns the output of the scan
    """
    try:
        output = None
        if scan["type"] == "ps":
            with psaudit_lock:
                output = psaudit.pwsh_run(scan["command"])
        elif scan["type"] == "az":
            with azaudit_lock:
                try:
                    output = azaudit.az_run(scan["command"])
                except Exception as e:
                    scan["comment"] = str(e)
        else:
            raise ValueError("Unsupported scan type")
        return get_result(output, scan)
    except Exception as e:
        return {"id": scan["id"], "name": scan["name"], "status": "Error", "comment": str(e)}


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


async def scanner_async(scan, psaudit, mcaudit, azaudit, loop, psaudit_lock, mcaudit_lock, azaudit_lock):
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, scanner, scan, psaudit, mcaudit, azaudit, psaudit_lock, mcaudit_lock, azaudit_lock)

async def main():
    args = parse_args()
    if args is None:
        return -1

    info("Starting AzureKitty, connecting... This may take some time. Be patient.")

    if not platform.machine() in ("AMD64", "x86_64"):
        warning("Some checks may not work on this architecture.")

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
    result_dict = {}

    loop = asyncio.get_running_loop()
    
    psaudit_lock = threading.Lock()
    mcaudit_lock = threading.Lock()
    azaudit_lock = threading.Lock()

    tasks = [scanner_async(scan, psaudit, mcaudit, azaudit, loop, psaudit_lock, mcaudit_lock, azaudit_lock) for scan in objects]
    completed, pending = await asyncio.wait(tasks)

    for task in completed:
        try:
            result = task.result()
            result_dict[result["id"]] = result
        except Exception as e:
            printf(f"Error during scan: {e}")

    if pending:
        printf("Cleaning up pending tasks...")
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                printf("Cancelled a pending task.")
            except Exception as e:
                printf(f"Error during handling pending task: {e}")

    success(f"Fully scanned the Azure/Office365 configuration.")

    for scan_id, scan in result_dict.items():
        print_audit_element(scan["id"], scan["name"], scan["status"])

    if args.output:
        cleaned_results = [{key: scan[key] for key in ["id", "name", "status", "comment"]} for scan in result_dict.values()]
        ObjectSerializer(cleaned_results, args.output, args.debug).serialize()

if __name__ == "__main__":
    asyncio.run(main())
