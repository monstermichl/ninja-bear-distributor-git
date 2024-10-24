# Make sure the script is executed in the example directory even if it's called from somewhere else.
pushd "${0%/*}/../.." # https://stackoverflow.com/a/207966

function _exit() {
    popd
    exit $1
}

# Install required build packages.
python3 -m pip install build wheel || _exit -1

# Build locally (https://packaging.python.org/en/latest/discussions/setup-py-deprecated/#what-commands-should-be-used-instead).
python3 -m build || _exit -2

# Install via pip (https://github.com/pypa/pip/issues/9110#issuecomment-723675528).
python3 -m pip install --force-reinstall . || _exit -3

# Exit script successfully.
_exit 0
