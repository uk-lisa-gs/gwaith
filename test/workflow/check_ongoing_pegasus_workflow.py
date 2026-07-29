"""Check an ongoing pegasus workflow.
This will print the pegasus-status output for the workflow, and then this script fails if the 
pegasus jobs has failed. This way we can monitor an ongoing workflow."""

import subprocess
import time
import sys

import argparse

parser = argparse.ArgumentParser()

parser.add_argument(
    "--time-delay",
    type=int,
    default=60,
    help="How long to wait (seconds) between runs of pegasus-status"
)

args = parser.parse_args()

# Give 30s extra time initially to allow the workflow to start up properly
time.sleep(30)

# Now enter a loop to run the status check until the workflow completes / fails

# When reading the pegasus-status output, we utilise the fact that the
# output is consistent.
# Examples come from https://pegasus.isi.edu/documentation/user-guide/monitoring-debugging-stats.html#pegasus-status

# A running workflow looks like this ():
# $ pegasus-status /Workflow/dags/directory
# STAT  IN_STATE  JOB
# Run      05:08  level-3-0
# Run      04:32   |-sleep_ID000005
# Run      04:27   \_subdax_level-2_ID000004
# Run      03:51      |-sleep_ID000003
# Run      03:46      \_subdax_level-1_ID000002
# Run      03:10         \_sleep_ID000001
# Summary: 6 Condor jobs total (R:6)

# UNREADY   READY     PRE  QUEUED    POST SUCCESS FAILURE %DONE
#       0       0       0       6       0       3       0  33.3
# Summary: 3 DAGs total (Running:3)

def check_status(lines: list[str]) -> str:
    """
    Parses the list of lines from the output of pegasus-status and 
    returns the workflow status as a single string.
    Additional checks are in place for fast-failure scenarios.

    Args:
        lines: A list of strings from the pegasus-status stdout.

    Returns:
        A string: 'RUNNING', 'SUCCESS', or 'FAILURE'.
    """

    # Check for immediate submission failure
    # A failed submission will have the line:
    # Summary: 1 DAG total (Failure:1)

    for line in lines:
        if line.startswith("Summary") and "(Failure" in line:
            print("Job Submission has failed 😭")
            return 'FAILURE'

    # Find the status summary line
    # This follows directly under the column header line which
    # starts "UNREADY"
    for i, line in enumerate(lines):
        if line.startswith("UNREADY"):
            if i + 1 < len(lines):
                status_line = lines[i+1]
                break
    else:
        # There should always be the UNREADY line, this indicates a problem
        # with this code itself, so raise an error
        raise RuntimeError(
            "No summary status line found in pegasus-status output."
        )

    # parse the status line
    stats = status_line.split()
    if len(stats) != 8:
        raise RuntimeError(
            "Could not parse status line, expected exactly 8 columns"
        )

    unready = int(stats[0])
    ready = int(stats[1])
    pre = int(stats[2])
    queued = int(stats[3])
    post = int(stats[4])
    # entry 5 is the raw number of successful jobs - without knowing the
    # total number of jobs, this is pretty useless
    failure = int(stats[6])
    pc_done = stats[7]

    if failure != 0:
        # Fast-fail if there have been any failures
        print("Workflow has failed 😭")
        return 'FAILURE'

    # If the workflow is finished, then these will all be zero
    finished = (unready + ready + pre + queued + post) == 0
    if finished and pc_done == "100.0":
        return 'SUCCESS'

    # nothing has indicated that the workflow has finished, so carry on
    return 'RUNNING'


while True:
    # Wait until the next iteration
    time.sleep(args.time_delay)
    # Run pegasus-status, capture the output, and print it.
    # Using text=True decodes stdout/stderr as text.
    result = subprocess.run(
        ["pegasus-status", "submitdir/work/"],
        capture_output=True, text=True, check=False
    )

    # Lets print the results to the console
    print(result.stdout)
    print(result.stderr, file=sys.stderr)

    lines = list(result.stdout.splitlines())

    status = check_status(lines)

    if status == 'SUCCESS':
        print("Workflow has finished successfully 🎉")
        sys.exit(0)
    elif status == 'FAILURE':
        # If this has failed, stop the workflow.
        subprocess.run(
            "export PEGASUS_UPDATE_PYTHONPATH=0; pegasus-remove submitdir/work/",
            shell=True, check=False, capture_output=True
        )
        # Wait to ensure it has fully finished before
        # uploading logs
        time.sleep(30)
        sys.exit(1)
    # If status is 'RUNNING', the loop continues.
