#!/bin/bash

# Usage: ./build_pyinstaller.sh <rebuild: yes/no> <ubuntu_version: 1804/2004/both> [BUILD_SUFFIX]

# Function to display help information
show_help() {
    cat << EOF
Usage: $0 <rebuild: yes/no> <ubuntu_version: 1804/2004/both> [BUILD_SUFFIX]

Arguments:
  -h, --hello       Show this help message
  rebuild           'yes' to rebuild images, 'no' to skip rebuilding
  ubuntu_version    '1804' for Ubuntu 18.04, '2004' for Ubuntu 20.04, 'both' for both versions
  [BUILD_SUFFIX]    Optional suffix to append to 'version' file

Examples:
  $0 yes both       # Rebuild and run both Ubuntu 18.04 & 20.04 images
  $0 no 1804        # Run only Ubuntu 18.04 without rebuilding
  $0 yes 2004       # Rebuild and run only Ubuntu 20.04
EOF
    exit 0
}

[[ "$1" == "-h" || "$1" == "--help" ]] && show_help

if [[ $# -lt 2 ]]; then
    echo "Error: Missing required arguments."
    show_help
fi

REBUILD=$1
UBUNTU_VERSION=$2
BUILD_SUFFIX=${3:-none}  # Default to 'none' if not provided

if [[ -f "version" ]]; then
    cp version version.bak
    BUILD_NUMBER=$(sed 's/[[:space:]]*$//' version)
else
    BUILD_NUMBER="UNKNOWN"
fi

update_version_file() {
    local version=$1
    local suffix_upper

    # Convert BUILD_SUFFIX to uppercase
    suffix_upper=$(echo "$BUILD_SUFFIX" | tr '[:lower:]' '[:upper:]')
    current_date=$(date "+%Y-%m-%d")

    if [[ "$suffix_upper" == "NONE" ]]; then
        echo -n "$BUILD_NUMBER - Compiled on Ubuntu $version on $current_date" > version
    else
        echo -n "$BUILD_NUMBER($suffix_upper) - Compiled on Ubuntu $version on $current_date" > version
        echo "Updated 'version' file for Ubuntu $version"
    fi
}

# Function to build a Docker image if requested
build_image() {
    local image_name=$1
    local dockerfile=$2

    if [[ "$REBUILD" == "yes" ]]; then
        echo ">>>>>> Building image: $image_name <<<<<<"
        docker build --no-cache -t "$image_name" -f "$dockerfile" .
    else
        echo ">>>>>> Skipping rebuild for: $image_name <<<<<<"
    fi
}

# Function to build and run the image
build_and_run() {
    local version=$1
    local dockerfile="Ubuntu${version}Dockerfile"
    local image_name="pyinstaller_b${version}"

    # Update the 'version' file before build
    update_version_file "$version"

    # Call build function
    build_image "$image_name" "$dockerfile"

    # Run container
    echo ">>>>>> Running container: $image_name <<<<<<"
    docker run --rm -v ./:/app -it "$image_name" pyinstaller --clean autotest.spec --log-level=DEBUG
    echo ">>>>>>> Done with image compilation on Ubuntu ${version} <<<<<<<"
}

# Process Ubuntu version selection
case "$UBUNTU_VERSION" in
    1804) build_and_run "1804" ;;
    2004) build_and_run "2004" ;;
    both)
        build_and_run "1804"
        build_and_run "2004"
        ;;
    *)
        echo "Error: Invalid Ubuntu version '$UBUNTU_VERSION'."
        show_help
        ;;
esac

# Restore original 'version' file
cp version.bak version
rm -f version.bak

echo ">>>>>> All Tasks Completed! <<<<<<"
