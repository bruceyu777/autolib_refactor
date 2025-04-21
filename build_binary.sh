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
BUILD_SUFFIX=$(echo "${3:-none}" | tr '[:lower:]' '[:upper:]')
REMOTE_HOST="fosqa@172.18.52.254"

if [[ -f "version" ]]; then
    cp version version.bak
    BUILD_NUMBER=$(sed 's/[[:space:]]*$//' version)
else
    echo "Error: 'version' file not found. Cannot proceed with build."
    exit 1
fi

update_version_file() {
    local version=$1
    current_date=$(date "+%Y-%m-%d")

    if [[ "$BUILD_SUFFIX" == "NONE" ]]; then
        echo -n "$BUILD_NUMBER - Compiled on Ubuntu $version on $current_date" > version
    else
        echo -n "$BUILD_NUMBER($BUILD_SUFFIX) - Compiled on Ubuntu $version on $current_date" > version
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

# Function to upload files to a remote host
upload_to_remote() {
    # Set target folder path based on BUILD_SUFFIX and BUILD_NUMBER
    if [[ "$BUILD_SUFFIX" == *"DEBUG"* ]]; then
        local date_suffix
        date_suffix=$(date "+%Y%m%d")
        target_folder="/tftp/work_directory/AutoLib/dev_builds/$date_suffix"
        download_url="https://releaseqa-imageserver.corp.fortinet.com/AutoLib/dev_builds/$date_suffix"

    else
        version_part="${BUILD_NUMBER%%B*}"
        build_part="build${BUILD_NUMBER##*B}"
        target_folder="/tftp/work_directory/AutoLib/$version_part/$build_part"
        download_url="https://releaseqa-imageserver.corp.fortinet.com/AutoLib/$version_part/$build_part"
    fi

    echo "Preparing to upload ./dist to $REMOTE_HOST:$target_folder ..."

    # Create remote folder if it doesn't exist
    if ! ssh "$REMOTE_HOST" "mkdir -p \"$target_folder\""; then
        echo "Error: Failed to create remote folder on $REMOTE_HOST. Skipping upload."
        return 1
    fi

    # Upload dist files
    if ! scp -r ./dist/* "$REMOTE_HOST:$target_folder/"; then
        echo "Error: Upload failed. Please verify network connectivity and target folder permissions."
        return 1
    fi

    files_to_upload=(
    "./AutolibDockerfile"
    "./env_field_description.yaml"
    )

    # Loop over files and transfer
    for file in "${files_to_upload[@]}"; do
        scp "$file" "$REMOTE_HOST:$target_folder/"
    done

    if [[ "$BUILD_SUFFIX" != *"DEBUG"* ]]; then
        echo "Uploading ./dist/autotest_1804 to $REMOTE_HOST:$target_folder ..."
        if ! scp ./dist/autotest_1804 "$REMOTE_HOST:/tftp/work_directory/AutoLib/autotest"; then
            echo "Error: Upload of autotest_1804 failed."
            return 1
        fi
    fi

    echo "******* DOWNLOAD URL: $download_url *******"
    echo ">>>>>>> Completed file upload <<<<<<<"
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

cp version.bak version
rm -f version.bak

if ! upload_to_remote; then
    echo "Warning: Upload to remote host failed. Please check logs above."
fi

echo ">>>>>> All Tasks Completed! <<<<<<"
