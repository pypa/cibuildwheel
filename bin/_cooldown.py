import os

# Number of days a release must age before our update scripts will pick it up.
# NOTE: keep this in sync with the Dependabot configuration in .github/dependabot.yml.
COOLDOWN_DAYS = 7

# Set CIBW_IGNORE_COOLDOWN to a truthy value to bypass the cooldown and always pick
# up the very latest releases regardless of age.
IGNORE_COOLDOWN = os.environ.get("CIBW_IGNORE_COOLDOWN", "").lower() in ("1", "true")
