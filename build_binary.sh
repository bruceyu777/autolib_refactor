#!/bin/bash

# Usage: ./build_pyinstaller.sh <rebuild: yes/no> <ubuntu_version: 1804/2004/both>

# Function to display help information
show_help() {
    echo "Usage: $0 <rebuild: yes/no> <ubuntu_version: 1804/2004/both>"
    echo
    echo "Options:"
    echo "  yes    Rebuild the Docker image(s) before running"
    echo "  no     Skip rebuilding and use existing image(s)"
    echo
    echo "  1804   Build and run for Ubuntu 18.04 only"
    echo "  2004   Build and run for Ubuntu 20.04 only"
    echo "  both   Build and run for both versions"
    echo
    echo "Examples:"
    echo "  $0 yes both     # Rebuild and run both Ubuntu 18.04 & 20.04 images"
    echo "  $0 no 1804      # Run only Ubuntu 18.04 without rebuilding"
    echo "  $0 yes 2004     # Rebuild and run only Ubuntu 20.04"
    echo
    exit 0
}

# Check if the user wants help
if [ "$1" == "-h" ] || [ "$1" == "--hello" ]; then
    show_help
fi

REBUILD=$1
UBUNTU_VERSION=$2

# Function to build and run the image
build_and_run() {
    local version=$1
    local dockerfile="Ubuntu${version}Dockerfile"
    local image_name="pyinstaller_b${version}"

    if [ "$REBUILD" == "yes" ]; then
        echo ">>>>>> Building image: $image_name <<<<<<"
        docker build --no-cache -t "$image_name" -f "$dockerfile" .
    else
        echo ">>>>>> Skipping rebuild for: $image_name <<<<<<"
    fi

    echo ">>>>>> Running container: $image_name <<<<<<"
    docker run --rm -v ./:/app -it "$image_name" pyinstaller --clean autotest.spec --log-level=DEBUG
    echo ">>>>>>> Done with image compilation on Ubuntu ${version} <<<<<<<"
}

# Validate input
if [ -z "$REBUILD" ] || [ -z "$UBUNTU_VERSION" ]; then
    echo "Error: Missing arguments."
    show_help
fi

# Determine which versions to build
if [ "$UBUNTU_VERSION" == "1804" ]; then
    build_and_run "1804"
elif [ "$UBUNTU_VERSION" == "2004" ]; then
    build_and_run "2004"
else
    build_and_run "1804"
    build_and_run "2004"
fi
