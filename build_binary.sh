#!/bin/bash

# ===========================
# Usage and Argument Parsing
# ===========================
show_help() {
    cat << EOF
Usage: $0 <rebuild: yes/no> <ubuntu_version: 1804/2004/both> [BUILD_SUFFIX]

Arguments:
  -h, --help         Show this help message
  rebuild            'yes' to rebuild images, 'no' to skip rebuilding
  ubuntu_version     '1804', '2004', or 'both'
  [BUILD_SUFFIX]     Optional suffix to append to 'version' file

Examples:
  $0 yes both        # Rebuild and run both Ubuntu 18.04 & 20.04 images
  $0 no 1804         # Run only Ubuntu 18.04 without rebuilding
EOF
    exit 0
}

[[ "$1" == "-h" || "$1" == "--help" ]] && show_help
[[ $# -lt 2 ]] && echo "Error: Missing required arguments." && show_help

REBUILD=$1
UBUNTU_VERSION=$2
BUILD_SUFFIX=$(echo "${3:-none}" | tr '[:lower:]' '[:upper:]')
REMOTE_HOST="fosqa@172.18.52.254"

[[ -f version ]] || { echo "Error: 'version' file not found."; exit 1; }
cp version version.bak
BUILD_NUMBER=$(sed 's/[[:space:]]*$//' version)

# =======================
# Utility Functions
# =======================

update_version_file() {
    local version=$1
    local current_date=$(date "+%Y-%m-%d")
    local suffix_str=""

    [[ "$BUILD_SUFFIX" != "NONE" ]] && suffix_str="($BUILD_SUFFIX)"

    echo -n "$BUILD_NUMBER$suffix_str - Compiled on Ubuntu $version on $current_date" > version
    echo "Updated 'version' file for Ubuntu $version"
}

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

build_and_run() {
    echo ">>>>>> Starting compilation on Ubuntu $version <<<<<<"
    local version=$1
    local dockerfile="Ubuntu${version}Dockerfile"
    local image_name="pyinstaller_b${version}"

    update_version_file "$version"
    build_image "$image_name" "$dockerfile"

    echo ">>>>>> Running container: $image_name <<<<<<"
    docker run --rm -v ./:/app -it "$image_name" pyinstaller --clean autotest.spec --log-level=DEBUG
    echo ">>>>>>> Done with image compilation on Ubuntu ${version} <<<<<<<"

    local output_file="./dist/autotest_${version}"
    echo "Binary path: $output_file" # This is the path being "returned"

    if [[ "$BUILD_SUFFIX" != *"DEBUG"* ]]; then
        upload_binary "$output_file" || return 1
    fi
}

upload_binary() {
    local file_path=$1
    local filename=$(basename "$file_path")
    local remote_path="/tftp/work_directory/AutoLib/$filename"

    echo "Uploading $file_path to $REMOTE_HOST:$remote_path ..."
    scp "$file_path" "$REMOTE_HOST:$remote_path" || {
        echo "Error: Upload of $filename failed."; return 1;
    }
}

upload_support_files() {
    local date_suffix=$(date "+%Y%m%d")

    if [[ "$BUILD_SUFFIX" == *"DEBUG"* ]]; then
        target_folder="/tftp/work_directory/AutoLib/dev_builds/$date_suffix"
        download_url="https://releaseqa-imageserver.corp.fortinet.com/AutoLib/dev_builds/$date_suffix"
    else
        version_part="${BUILD_NUMBER%%B*}"
        build_part="build${BUILD_NUMBER##*B}"
        target_folder="/tftp/work_directory/AutoLib/$version_part/$build_part"
        download_url="https://releaseqa-imageserver.corp.fortinet.com/AutoLib/$version_part/$build_part"
    fi

    echo "Preparing to upload ./dist to $REMOTE_HOST:$target_folder ..."
    ssh "$REMOTE_HOST" "mkdir -p \"$target_folder\"" || {
        echo "Error: Failed to create remote folder."; return 1;
    }

    scp -r ./dist/* "$REMOTE_HOST:$target_folder/" || {
        echo "Error: Dist upload failed."; return 1;
    }

    local files_to_upload=(
        "./AutolibDockerfile"
        "./env_field_description.yaml"
        "./changelog.md"
    )

    for file in "${files_to_upload[@]}"; do
        scp "$file" "$REMOTE_HOST:$target_folder/"
    done

    echo "******* DOWNLOAD URL: $download_url *******"
    echo ">>>>>>> Completed file upload <<<<<<<"
}

build_binary() {
    local versions=()

    case "$UBUNTU_VERSION" in
        1804) versions=("1804") ;;
        2004) versions=("2004") ;;
        both) versions=("1804" "2004") ;;
        *) echo "Error: Invalid Ubuntu version '$UBUNTU_VERSION'."; show_help ;;
    esac

    echo "Selected Ubuntu versions: ${versions[@]}"

    for version in "${versions[@]}"; do
        build_and_run "$version" || return 1
    done

    upload_support_files
}

# ============ Entry ============
build_binary
cp version.bak version && rm -f version.bak

echo ">>>>>> All Tasks Completed! <<<<<<"
