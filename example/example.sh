# Make sure the script is executed in the example directory even if it's called from somewhere else.
pushd "${0%/*}" # https://stackoverflow.com/a/207966

OUTPUT_DIR=generated

# Create output dir.
if [ ! -d ${OUTPUT_DIR} ]; then
    mkdir ${OUTPUT_DIR}
fi

# Generate Java and Typescript files from test config.
ninja-bear -c test-config.yaml -o generated $*

# Go back to original directory.
popd
