# Make sure the script is executed from the current directory even if it's called from somewhere else.
pushd "${0%/*}" # https://stackoverflow.com/a/207966

function _exit() {
    popd
    exit $1
}

./install.sh || _exit -1
./test.sh || _exit -2

# Exit script successfully.
_exit 0
