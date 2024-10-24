# Make sure the script is executed from the base directory even if it's called from somewhere else.
pushd "${0%/*}/../.." # https://stackoverflow.com/a/207966

function _exit() {
    popd
    exit $1
}

# Install required test packages.
python -m pip install coverage

# Run unit tests.
python3 -m coverage run -m unittest || _exit -1

# Generate HTML coverage report.
python3 -m coverage html

# Print coverage report to stdout.
python3 -m coverage report

# Go back to original directory.
_exit 0
