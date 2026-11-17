"""
Checks Cornell's Class Roster API for a section and sends a push
notification (via ntfy) when it is no longer closed.

Settings come from environment variables (set in the GitHub workflow):
  ROSTER      e.g. SP27
  SUBJECT     e.g. HADM
  CATALOG     e.g. 2351
  CLASS_NBR   e.g. 15810   (the 5-digit class number)
  NTFY_TOPIC  your private ntfy topic name (store as a GitHub secret)
"""

import json
import os
import sys
import urllib.request

ROSTER = os.environ.get("ROSTER", "SP27")
SUBJECT = os.environ.get("SUBJECT", "HADM")
CATALOG = os.environ.get("CATALOG", "2351")
CLASS_NBR = int(os.environ.get("CLASS_NBR", "15810"))
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

API = (
    "https://classes.cornell.edu/api/2.0/search/classes.json"
    f"?roster={ROSTER}&subject={SUBJECT}&q={CATALOG}"
)
STATUS_NAMES = {"O": "OPEN", "C": "Closed", "W": "WAITLIST"}


def find_section(node):
    """Walk the JSON and return the section dict whose classNbr matches."""
    if isinstance(node, dict):
        if node.get("classNbr") == CLASS_NBR:
            return node
        for value in node.values():
            found = find_section(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_section(item)
            if found:
                return found
    return None


def notify(title, message, priority="urgent"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode(),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": "rotating_light",
            "Click": "https://studentcenter.cornell.edu",
        },
    )
    urllib.request.urlopen(req, timeout=20)


def main():
    req = urllib.request.Request(API, headers={"User-Agent": "course-alert"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    section = find_section(data)
    if section is None:
        # Fail loudly so GitHub emails you instead of silently checking nothing.
        sys.exit(f"Class number {CLASS_NBR} not found in {API}")

    status = section.get("openStatus", "?")
    label = f"{SUBJECT} {CATALOG}-{section.get('section', '?')} ({CLASS_NBR})"
    print(f"{label}: openStatus={status!r}")

    if status != "C":
        notify(
            f"{label} is {STATUS_NAMES.get(status, status)}",
            "A seat may be open. Go enroll in Student Center now.",
        )
        print("Notification sent.")


if __name__ == "__main__":
    main()
