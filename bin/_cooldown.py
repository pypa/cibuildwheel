import os

# Number of days a release must age before the update scripts will pick it up.
# This is intentionally different from Dependabot because we want to have these
# updates coming faster to align with the latest releases.
# NOTE: Keep this in sync with noxfile.py's update_constraints session.
COOLDOWN_DAYS = 3

# Set CIBW_IGNORE_COOLDOWN to a truthy value to bypass the cooldown and always pick
# up the very latest releases regardless of age.
IGNORE_COOLDOWN = os.environ.get("CIBW_IGNORE_COOLDOWN", "").lower() in ("1", "true")
