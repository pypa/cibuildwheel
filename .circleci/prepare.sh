set -o errexit
set -o xtrace

$PYTHON --version
$PYTHON -m pip --version
sudo $PYTHON -m pip uninstall -y poetry
$PYTHON -m pip install --user --ignore-installed virtualenv==20.0.21
$PYTHON -m virtualenv -p $PYTHON venv
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/python -m pip freeze
venv/bin/python --version
