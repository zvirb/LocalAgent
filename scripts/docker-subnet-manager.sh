#!/bin/bash
#
# Docker Network Subnet Manager - Bash Implementation
# ===================================================
#
# A comprehensive Bash script for Docker network subnet management.
# Scans existing networks, finds available subnets in 172.16.0.0/12 range,
# and provides tools for updating docker-compose.yml files.
#
# Features:
# - Scan existing Docker networks for subnet usage
# - Find next available subnet in 172.16.0.0/12 range
# - Update docker-compose.yml files with new network configurations
# - Generate override files
# - Handle subnet exhaustion scenarios
# - Backup and validation mechanisms
#
# Usage: ./docker-subnet-manager.sh [options]
#

set -euo pipefail

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly LOG_FILE="${SCRIPT_DIR}/docker_subnet_manager_$(date +%Y%m%d_%H%M%S).log"

# Default configuration
BASE_DIR="."
SUBNET_SIZE="16"
DRY_RUN=false
VERBOSE=false
INTERACTIVE=false
NETWORK_NAME=""
COMPOSE_FILE=""

# Network configuration
readonly PRIVATE_RANGE_START="172.16.0.0"
readonly PRIVATE_RANGE_BITS="12"
readonly PRIVATE_RANGE="${PRIVATE_RANGE_START}/${PRIVATE_RANGE_BITS}"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[0;37m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    local message="$1"
    echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
}

log_warn() {
    local message="$1"
    echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE" >&2
}

log_debug() {
    local message="$1"
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
    else
        echo "[DEBUG] $message" >> "$LOG_FILE"
    fi
}

# Utility functions
print_header() {
    local title="$1"
    local width=60
    local padding=$(( (width - ${#title} - 2) / 2 ))
    
    echo -e "${BOLD}${CYAN}"
    printf "═%.0s" $(seq 1 $width)
    echo
    printf "%*s %s %*s\n" $padding "" "$title" $padding ""
    printf "═%.0s" $(seq 1 $width)
    echo -e "${NC}"
}

print_section() {
    local title="$1"
    echo -e "\n${BOLD}${WHITE}$title${NC}"
    echo -e "${WHITE}$(printf '─%.0s' $(seq 1 ${#title}))${NC}"
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_debug "Docker check passed"
    return 0
}

# Check if required tools are available
check_dependencies() {
    local missing_tools=()
    
    for tool in docker yq jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_warn "Missing optional tools: ${missing_tools[*]}"
        log_warn "Some features may not be available"
        log_warn "Install with: sudo apt-get install ${missing_tools[*]} (Ubuntu/Debian)"
        log_warn "Or: brew install ${missing_tools[*]} (macOS)"
    fi
}

# Scan existing Docker networks
scan_docker_networks() {
    log_info "Scanning existing Docker networks..."
    
    if ! check_docker; then
        log_warn "Docker not available, using empty network list"
        return 0
    fi
    
    # Create temporary file for network data
    local network_file=$(mktemp)
    local subnet_file=$(mktemp)
    
    # Clean up temp files on exit
    trap "rm -f $network_file $subnet_file" RETURN
    
    # Get all networks
    docker network ls --format "{{.Name}}" > "$network_file"
    
    log_debug "Found $(wc -l < "$network_file") Docker networks"
    
    # Extract subnet information
    while IFS= read -r network_name; do
        if [[ -z "$network_name" ]]; then
            continue
        fi
        
        log_debug "Inspecting network: $network_name"
        
        # Get subnet from network inspection
        local subnet_info
        subnet_info=$(docker network inspect "$network_name" 2>/dev/null | \
            jq -r '.[0].IPAM.Config[]?.Subnet // empty' 2>/dev/null || true)
        
        if [[ -n "$subnet_info" && "$subnet_info" != "null" ]]; then
            # Check if subnet is in our managed range (172.16.0.0/12)
            if is_subnet_in_range "$subnet_info" "$PRIVATE_RANGE"; then
                echo "$network_name:$subnet_info" >> "$subnet_file"
                log_debug "Network $network_name uses subnet $subnet_info"
            fi
        fi
    done < "$network_file"
    
    if [[ -f "$subnet_file" ]]; then
        log_info "Found $(wc -l < "$subnet_file") networks using managed subnets:"
        while IFS=: read -r network subnet; do
            log_info "  • $network: $subnet"
        done < "$subnet_file"
        
        # Store for later use
        cp "$subnet_file" "${SCRIPT_DIR}/.used_subnets_cache"
    else
        log_info "No networks found using managed subnets"
        touch "${SCRIPT_DIR}/.used_subnets_cache"
    fi
}

# Check if a subnet is within a given range
is_subnet_in_range() {
    local subnet="$1"
    local range="$2"
    
    # Extract network parts
    local subnet_ip subnet_bits range_ip range_bits
    IFS='/' read -r subnet_ip subnet_bits <<< "$subnet"
    IFS='/' read -r range_ip range_bits <<< "$range"
    
    # Convert IP addresses to integers for comparison
    local subnet_int range_int
    subnet_int=$(ip_to_int "$subnet_ip")
    range_int=$(ip_to_int "$range_ip")
    
    # Calculate network masks
    local subnet_mask range_mask
    subnet_mask=$((0xffffffff << (32 - subnet_bits)))
    range_mask=$((0xffffffff << (32 - range_bits)))
    
    # Check if subnet network is within range network
    local subnet_network range_network
    subnet_network=$((subnet_int & range_mask))
    range_network=$((range_int & range_mask))
    
    [[ $subnet_network -eq $range_network ]]
}

# Convert IP address to integer
ip_to_int() {
    local ip="$1"
    local a b c d
    IFS='.' read -r a b c d <<< "$ip"
    echo $((a * 256**3 + b * 256**2 + c * 256 + d))
}

# Convert integer to IP address
int_to_ip() {
    local int="$1"
    local a b c d
    a=$((int >> 24 & 255))
    b=$((int >> 16 & 255))
    c=$((int >> 8 & 255))
    d=$((int & 255))
    echo "$a.$b.$c.$d"
}

# Find next available subnet
find_next_available_subnet() {
    local subnet_size="${1:-$SUBNET_SIZE}"
    
    log_info "Finding next available /$subnet_size subnet in $PRIVATE_RANGE"
    
    # Load used subnets
    local used_subnets_file="${SCRIPT_DIR}/.used_subnets_cache"
    if [[ ! -f "$used_subnets_file" ]]; then
        scan_docker_networks
    fi
    
    # Calculate subnet increment based on size
    local increment=$((2**(32-subnet_size)))
    
    # Start from the beginning of our range
    local range_start=$(ip_to_int "172.16.0.0")
    local range_end=$(ip_to_int "172.31.255.255")
    
    log_debug "Checking subnets with increment $increment from $(int_to_ip $range_start) to $(int_to_ip $range_end)"
    
    # Iterate through possible subnet starting addresses
    for ((subnet_start = range_start; subnet_start <= range_end; subnet_start += increment)); do
        local candidate_ip candidate_subnet
        candidate_ip=$(int_to_ip $subnet_start)
        candidate_subnet="$candidate_ip/$subnet_size"
        
        log_debug "Checking candidate subnet: $candidate_subnet"
        
        # Check if this subnet conflicts with any used subnet
        local conflict_found=false
        
        if [[ -s "$used_subnets_file" ]]; then
            while IFS=: read -r network used_subnet; do
                if subnets_overlap "$candidate_subnet" "$used_subnet"; then
                    log_debug "Conflict found with $network ($used_subnet)"
                    conflict_found=true
                    break
                fi
            done < "$used_subnets_file"
        fi
        
        if [[ "$conflict_found" == "false" ]]; then
            echo "$candidate_subnet"
            log_info "Found available subnet: $candidate_subnet"
            return 0
        fi
    done
    
    log_error "No available /$subnet_size subnets found in range $PRIVATE_RANGE"
    return 1
}

# Check if two subnets overlap
subnets_overlap() {
    local subnet1="$1"
    local subnet2="$2"
    
    # Extract IP and bits for both subnets
    local ip1 bits1 ip2 bits2
    IFS='/' read -r ip1 bits1 <<< "$subnet1"
    IFS='/' read -r ip2 bits2 <<< "$subnet2"
    
    # Convert to integers
    local int1 int2
    int1=$(ip_to_int "$ip1")
    int2=$(ip_to_int "$ip2")
    
    # Calculate network addresses using the smaller subnet mask (larger prefix)
    local smaller_bits mask1 mask2
    if [[ $bits1 -le $bits2 ]]; then
        smaller_bits=$bits1
    else
        smaller_bits=$bits2
    fi
    
    local mask=$((0xffffffff << (32 - smaller_bits)))
    
    local network1 network2
    network1=$((int1 & mask))
    network2=$((int2 & mask))
    
    # Subnets overlap if their network addresses are the same when using the smaller mask
    [[ $network1 -eq $network2 ]]
}

# Find docker-compose files
find_docker_compose_files() {
    local base_dir="${1:-$BASE_DIR}"
    
    log_info "Scanning for docker-compose files in $base_dir..."
    
    local compose_files=()
    
    # Find various docker-compose file patterns
    while IFS= read -r -d '' file; do
        compose_files+=("$file")
    done < <(find "$base_dir" \( -name "docker-compose.yml" -o \
                                 -name "docker-compose.yaml" -o \
                                 -name "docker-compose.*.yml" -o \
                                 -name "docker-compose.*.yaml" \) \
                                 -type f -print0 2>/dev/null)
    
    log_info "Found ${#compose_files[@]} docker-compose files"
    
    for file in "${compose_files[@]}"; do
        log_debug "  • $file"
    done
    
    printf '%s\n' "${compose_files[@]}"
}

# Extract networks from docker-compose file
extract_compose_networks() {
    local compose_file="$1"
    
    log_debug "Extracting networks from $compose_file"
    
    if ! [[ -f "$compose_file" ]]; then
        log_error "Compose file not found: $compose_file"
        return 1
    fi
    
    # Use yq if available, otherwise fall back to grep/awk
    if command -v yq &> /dev/null; then
        yq eval '.networks // {} | to_entries | .[] | .key + ":" + (.value.ipam.config[0].subnet // "")' "$compose_file" 2>/dev/null | \
            grep -v ':$' || true
    else
        # Fallback method using grep and awk (less reliable but works)
        log_warn "yq not available, using fallback method for parsing YAML"
        
        # Extract network sections (basic approach)
        awk '/^networks:$/,/^[a-zA-Z]/ {
            if (/^  [a-zA-Z_-]+:$/) {
                gsub(/:$/, "", $1)
                gsub(/^  /, "", $1)
                network = $1
            }
            if (/subnet:/) {
                gsub(/.*subnet: */, "")
                gsub(/ *$/, "")
                if ($0 != "" && network != "") {
                    print network ":" $0
                    network = ""
                }
            }
        }' "$compose_file" 2>/dev/null || true
    fi
}

# Update docker-compose file with new network
update_compose_file() {
    local compose_file="$1"
    local network_name="$2"
    local subnet="$3"
    local backup="${4:-true}"
    
    log_info "Updating $compose_file with network $network_name -> $subnet"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would update $compose_file"
        return 0
    fi
    
    if ! [[ -f "$compose_file" ]]; then
        log_error "Compose file not found: $compose_file"
        return 1
    fi
    
    # Create backup if requested
    if [[ "$backup" == "true" ]]; then
        local backup_file="${compose_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$compose_file" "$backup_file"
        log_info "Created backup: $backup_file"
    fi
    
    # Calculate gateway (first usable IP in subnet)
    local gateway
    gateway=$(calculate_gateway "$subnet")
    
    # Use yq to update the file if available
    if command -v yq &> /dev/null; then
        # Create network configuration using yq
        yq eval ".networks.\"$network_name\".driver = \"bridge\" | 
                 .networks.\"$network_name\".ipam.config[0].subnet = \"$subnet\" |
                 .networks.\"$network_name\".ipam.config[0].gateway = \"$gateway\"" \
                 -i "$compose_file"
        
        log_info "Successfully updated $compose_file using yq"
        return 0
    else
        log_warn "yq not available, using manual YAML manipulation"
        
        # Fallback: manual YAML manipulation (more fragile)
        local temp_file=$(mktemp)
        trap "rm -f $temp_file" RETURN
        
        # Check if networks section exists
        if grep -q "^networks:" "$compose_file"; then
            # Networks section exists, add/update network
            awk -v network="$network_name" -v subnet="$subnet" -v gateway="$gateway" '
            BEGIN { in_networks = 0; network_found = 0; added = 0 }
            /^networks:$/ { in_networks = 1; print; next }
            /^[a-zA-Z]/ && in_networks && !/^  / { 
                if (!network_found && !added) {
                    printf "  %s:\n", network
                    printf "    driver: bridge\n"
                    printf "    ipam:\n"
                    printf "      config:\n"
                    printf "        - subnet: %s\n", subnet
                    printf "          gateway: %s\n", gateway
                    added = 1
                }
                in_networks = 0
                print
                next
            }
            in_networks && /^  / && $1 == network":" {
                network_found = 1
                printf "  %s:\n", network
                printf "    driver: bridge\n"
                printf "    ipam:\n"
                printf "      config:\n"
                printf "        - subnet: %s\n", subnet
                printf "          gateway: %s\n", gateway
                # Skip existing network config
                while ((getline next_line) > 0 && next_line ~ /^    /) continue
                if (next_line) print next_line
                next
            }
            END {
                if (in_networks && !network_found && !added) {
                    printf "  %s:\n", network
                    printf "    driver: bridge\n"
                    printf "    ipam:\n"
                    printf "      config:\n"
                    printf "        - subnet: %s\n", subnet
                    printf "          gateway: %s\n", gateway
                }
            }
            { print }
            ' "$compose_file" > "$temp_file"
        else
            # No networks section, add one at the end
            cp "$compose_file" "$temp_file"
            cat >> "$temp_file" << EOF

networks:
  $network_name:
    driver: bridge
    ipam:
      config:
        - subnet: $subnet
          gateway: $gateway
EOF
        fi
        
        # Replace original file
        mv "$temp_file" "$compose_file"
        log_info "Successfully updated $compose_file using manual method"
        return 0
    fi
}

# Calculate gateway IP for a subnet (first usable IP)
calculate_gateway() {
    local subnet="$1"
    local ip bits
    IFS='/' read -r ip bits <<< "$subnet"
    
    local ip_int gateway_int
    ip_int=$(ip_to_int "$ip")
    gateway_int=$((ip_int + 1))
    
    int_to_ip $gateway_int
}

# Generate docker-compose override file
generate_override_file() {
    local base_compose_file="$1"
    local network_name="$2"
    local subnet="$3"
    
    local override_file="$(dirname "$base_compose_file")/docker-compose.override.yml"
    
    log_info "Generating override file: $override_file"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate $override_file"
        return 0
    fi
    
    local gateway
    gateway=$(calculate_gateway "$subnet")
    
    cat > "$override_file" << EOF
version: '3.8'

# Auto-generated Docker Compose override for network subnet management
# Generated by: $SCRIPT_NAME
# Timestamp: $(date)

networks:
  $network_name:
    driver: bridge
    ipam:
      config:
        - subnet: $subnet
          gateway: $gateway
EOF
    
    log_info "Generated override file: $override_file"
    echo "$override_file"
}

# Handle subnet exhaustion
handle_subnet_exhaustion() {
    local requested_size="${1:-$SUBNET_SIZE}"
    
    log_warn "Handling subnet exhaustion for /$requested_size subnets"
    
    echo -e "\n${YELLOW}⚠️  Subnet Exhaustion Solutions:${NC}"
    
    # Try smaller subnet sizes
    echo -e "\n${BLUE}1. Try smaller subnet sizes:${NC}"
    for size in $((requested_size + 1)) $((requested_size + 2)) $((requested_size + 3)); do
        if [[ $size -le 30 ]]; then
            local smaller_subnet
            if smaller_subnet=$(find_next_available_subnet "$size" 2>/dev/null); then
                echo -e "   ✅ Available /$size subnet: $smaller_subnet"
            else
                echo -e "   ❌ No /$size subnets available"
            fi
        fi
    done
    
    # Suggest cleanup
    echo -e "\n${BLUE}2. Clean up unused Docker networks:${NC}"
    echo "   docker network prune -f"
    
    # Show network usage
    echo -e "\n${BLUE}3. Current network usage:${NC}"
    if [[ -f "${SCRIPT_DIR}/.used_subnets_cache" ]]; then
        while IFS=: read -r network subnet; do
            echo "   • $network: $subnet"
        done < "${SCRIPT_DIR}/.used_subnets_cache"
    fi
    
    # Suggest alternative ranges
    echo -e "\n${BLUE}4. Consider alternative private IP ranges:${NC}"
    echo "   • 10.0.0.0/8 (Class A)"
    echo "   • 192.168.0.0/16 (Class C)"
    
    echo -e "\n${BLUE}5. Use external networks:${NC}"
    echo "   Create networks manually with 'docker network create' and reference them as external"
}

# Generate comprehensive report
generate_report() {
    local output_file="${1:-subnet_report.json}"
    
    log_info "Generating comprehensive subnet report"
    
    # Scan current state
    scan_docker_networks
    
    local used_subnets_file="${SCRIPT_DIR}/.used_subnets_cache"
    local compose_files
    mapfile -t compose_files < <(find_docker_compose_files)
    
    # Create JSON report
    local timestamp=$(date -Iseconds)
    
    cat > "$output_file" << EOF
{
  "scan_timestamp": "$timestamp",
  "base_directory": "$(realpath "$BASE_DIR")",
  "management_range": "$PRIVATE_RANGE",
  "statistics": {
    "total_used_subnets": $(wc -l < "$used_subnets_file" 2>/dev/null || echo 0),
    "compose_files_found": ${#compose_files[@]}
  },
  "docker_networks": {
EOF
    
    # Add Docker networks
    local first=true
    if [[ -s "$used_subnets_file" ]]; then
        while IFS=: read -r network subnet; do
            if [[ "$first" == "true" ]]; then
                first=false
            else
                echo "," >> "$output_file"
            fi
            echo -n "    \"$network\": \"$subnet\"" >> "$output_file"
        done < "$used_subnets_file"
    fi
    
    cat >> "$output_file" << EOF

  },
  "compose_files": [
EOF
    
    # Add compose files
    for i in "${!compose_files[@]}"; do
        echo -n "    \"${compose_files[i]}\"" >> "$output_file"
        if [[ $i -lt $((${#compose_files[@]} - 1)) ]]; then
            echo "," >> "$output_file"
        else
            echo >> "$output_file"
        fi
    done
    
    cat >> "$output_file" << EOF
  ],
  "next_available_subnets": {
EOF
    
    # Find next available subnets of different sizes
    local sizes=(16 24 25 26)
    for i in "${!sizes[@]}"; do
        local size=${sizes[i]}
        local next_subnet
        
        if next_subnet=$(find_next_available_subnet "$size" 2>/dev/null); then
            echo -n "    \"/$size\": \"$next_subnet\"" >> "$output_file"
        else
            echo -n "    \"/$size\": \"EXHAUSTED\"" >> "$output_file"
        fi
        
        if [[ $i -lt $((${#sizes[@]} - 1)) ]]; then
            echo "," >> "$output_file"
        else
            echo >> "$output_file"
        fi
    done
    
    cat >> "$output_file" << EOF
  }
}
EOF
    
    log_info "Report generated: $output_file"
}

# Interactive mode functions
interactive_main_menu() {
    while true; do
        print_header "Docker Subnet Manager - Interactive Mode"
        
        echo -e "\n${BOLD}Available Actions:${NC}"
        echo "  1. 📊 Generate subnet usage report"
        echo "  2. 🔍 Find next available subnet"
        echo "  3. 📝 Update docker-compose.yml file"
        echo "  4. 📋 Generate override file"
        echo "  5. 🧹 Clean up unused networks"
        echo "  6. 📈 Show current status"
        echo "  7. ❓ Help"
        echo "  8. 🚪 Exit"
        
        echo -n -e "\n${BOLD}Select an option (1-8):${NC} "
        read -r choice
        
        case $choice in
            1) interactive_generate_report ;;
            2) interactive_find_subnet ;;
            3) interactive_update_compose ;;
            4) interactive_generate_override ;;
            5) interactive_cleanup ;;
            6) interactive_show_status ;;
            7) show_help ;;
            8) echo -e "\n👋 Goodbye!"; break ;;
            *) echo -e "${RED}❌ Invalid choice. Please select 1-8.${NC}" ;;
        esac
        
        echo -e "\nPress Enter to continue..."
        read -r
    done
}

interactive_generate_report() {
    print_section "Generate Subnet Usage Report"
    
    echo -n "Enter output filename [subnet_report.json]: "
    read -r filename
    filename=${filename:-subnet_report.json}
    
    if [[ ! "$filename" =~ \.json$ ]]; then
        filename="${filename}.json"
    fi
    
    echo -e "\n⏳ Generating report..."
    if generate_report "$filename"; then
        echo -e "${GREEN}✅ Report generated successfully: $filename${NC}"
        
        if command -v jq &> /dev/null; then
            echo -e "\n${BOLD}Quick Summary:${NC}"
            local used_count=$(jq -r '.statistics.total_used_subnets' "$filename")
            local compose_count=$(jq -r '.statistics.compose_files_found' "$filename")
            echo "  • Used subnets: $used_count"
            echo "  • Compose files found: $compose_count"
            
            echo -e "\n${BOLD}Next available subnets:${NC}"
            jq -r '.next_available_subnets | to_entries[] | "  • " + .key + ": " + .value' "$filename"
        fi
    else
        echo -e "${RED}❌ Failed to generate report${NC}"
    fi
}

interactive_find_subnet() {
    print_section "Find Next Available Subnet"
    
    echo -n "Enter subnet size (16, 24, 25, 26) [16]: "
    read -r size
    size=${size:-16}
    
    if ! [[ "$size" =~ ^(16|24|25|26|27|28)$ ]]; then
        echo -e "${RED}❌ Invalid subnet size. Using /16${NC}"
        size=16
    fi
    
    echo -e "\n⏳ Finding available /$size subnet..."
    
    if next_subnet=$(find_next_available_subnet "$size"); then
        echo -e "${GREEN}✅ Found available subnet: $next_subnet${NC}"
        echo -e "\n${BOLD}Network Configuration:${NC}"
        echo "networks:"
        echo "  your-network-name:"
        echo "    driver: bridge"
        echo "    ipam:"
        echo "      config:"
        echo "        - subnet: $next_subnet"
        echo "          gateway: $(calculate_gateway "$next_subnet")"
    else
        echo -e "${RED}❌ No available /$size subnets found${NC}"
        handle_subnet_exhaustion "$size"
    fi
}

interactive_update_compose() {
    print_section "Update Docker Compose File"
    
    # Find compose files
    mapfile -t compose_files < <(find_docker_compose_files)
    
    if [[ ${#compose_files[@]} -eq 0 ]]; then
        echo -e "${RED}❌ No docker-compose files found in current directory${NC}"
        return
    fi
    
    echo "Available docker-compose.yml files:"
    for i in "${!compose_files[@]}"; do
        echo "  $((i + 1)). ${compose_files[i]}"
    done
    
    echo -n -e "\nSelect file to update (number): "
    read -r file_index
    
    if ! [[ "$file_index" =~ ^[0-9]+$ ]] || [[ $file_index -lt 1 ]] || [[ $file_index -gt ${#compose_files[@]} ]]; then
        echo -e "${RED}❌ Invalid file selection${NC}"
        return
    fi
    
    local selected_file="${compose_files[$((file_index - 1))]}"
    
    echo -n "Enter network name to update/create: "
    read -r network_name
    
    if [[ -z "$network_name" ]]; then
        echo -e "${RED}❌ Network name cannot be empty${NC}"
        return
    fi
    
    echo -n "Enter subnet size (16, 24, 25, 26) [16]: "
    read -r size
    size=${size:-16}
    
    if next_subnet=$(find_next_available_subnet "$size"); then
        echo -e "\n${GREEN}✅ Found available subnet: $next_subnet${NC}"
        echo -n "Update $selected_file with network '$network_name' -> $next_subnet? (y/n): "
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            if update_compose_file "$selected_file" "$network_name" "$next_subnet"; then
                echo -e "${GREEN}✅ Docker compose file updated successfully${NC}"
                # Add to used subnets cache
                echo "$network_name:$next_subnet" >> "${SCRIPT_DIR}/.used_subnets_cache"
            else
                echo -e "${RED}❌ Failed to update docker compose file${NC}"
            fi
        else
            echo -e "${YELLOW}❌ Update cancelled${NC}"
        fi
    else
        echo -e "${RED}❌ No available subnets found${NC}"
        handle_subnet_exhaustion "$size"
    fi
}

interactive_generate_override() {
    print_section "Generate Docker Compose Override"
    
    mapfile -t compose_files < <(find_docker_compose_files)
    
    if [[ ${#compose_files[@]} -eq 0 ]]; then
        echo -e "${RED}❌ No docker-compose files found${NC}"
        return
    fi
    
    echo "Available docker-compose.yml files:"
    for i in "${!compose_files[@]}"; do
        echo "  $((i + 1)). ${compose_files[i]}"
    done
    
    echo -n -e "\nSelect base file (number): "
    read -r file_index
    
    if ! [[ "$file_index" =~ ^[0-9]+$ ]] || [[ $file_index -lt 1 ]] || [[ $file_index -gt ${#compose_files[@]} ]]; then
        echo -e "${RED}❌ Invalid file selection${NC}"
        return
    fi
    
    local selected_file="${compose_files[$((file_index - 1))]}"
    
    echo -n "Enter network name for override: "
    read -r network_name
    
    if [[ -z "$network_name" ]]; then
        echo -e "${RED}❌ Network name cannot be empty${NC}"
        return
    fi
    
    echo -n "Enter subnet size (16, 24, 25, 26) [16]: "
    read -r size
    size=${size:-16}
    
    if next_subnet=$(find_next_available_subnet "$size"); then
        echo -e "\n${GREEN}✅ Found available subnet: $next_subnet${NC}"
        echo -n "Generate override file for network '$network_name' -> $next_subnet? (y/n): "
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            if override_path=$(generate_override_file "$selected_file" "$network_name" "$next_subnet"); then
                echo -e "${GREEN}✅ Override file generated: $override_path${NC}"
                # Add to used subnets cache
                echo "$network_name:$next_subnet" >> "${SCRIPT_DIR}/.used_subnets_cache"
            else
                echo -e "${RED}❌ Failed to generate override file${NC}"
            fi
        else
            echo -e "${YELLOW}❌ Generation cancelled${NC}"
        fi
    else
        echo -e "${RED}❌ No available subnets found${NC}"
        handle_subnet_exhaustion "$size"
    fi
}

interactive_cleanup() {
    print_section "Network Cleanup"
    
    echo -e "${YELLOW}⚠️  This will remove unused Docker networks.${NC}"
    echo "Make sure no containers are using networks you want to remove."
    echo
    
    if check_docker; then
        echo "Current Docker networks:"
        docker network ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}" || true
        echo
    fi
    
    echo -n "Continue with network cleanup? (y/n): "
    read -r confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        if check_docker; then
            echo -e "\n⏳ Cleaning up unused networks..."
            if docker network prune -f; then
                echo -e "${GREEN}✅ Network cleanup completed${NC}"
                # Refresh cache
                scan_docker_networks
            else
                echo -e "${RED}❌ Network cleanup failed${NC}"
            fi
        else
            echo -e "${RED}❌ Docker not available${NC}"
        fi
    else
        echo -e "${YELLOW}❌ Cleanup cancelled${NC}"
    fi
}

interactive_show_status() {
    print_section "Current Status"
    
    # Scan current networks
    scan_docker_networks
    
    local used_subnets_file="${SCRIPT_DIR}/.used_subnets_cache"
    local used_count=0
    
    if [[ -f "$used_subnets_file" ]]; then
        used_count=$(wc -l < "$used_subnets_file")
    fi
    
    echo -e "${BOLD}📊 Subnet Usage Summary:${NC}"
    echo "  • Management range: $PRIVATE_RANGE"
    echo "  • Used subnets: $used_count"
    
    if [[ $used_count -gt 0 ]]; then
        echo -e "\n${BOLD}🌐 Used Subnets:${NC}"
        while IFS=: read -r network subnet; do
            echo "  • $network: $subnet"
        done < "$used_subnets_file"
    fi
    
    echo -e "\n${BOLD}🆕 Next Available Subnets:${NC}"
    for size in 16 24 25 26; do
        if next_subnet=$(find_next_available_subnet "$size" 2>/dev/null); then
            echo -e "  • /${size}: ${GREEN}$next_subnet${NC}"
        else
            echo -e "  • /${size}: ${RED}EXHAUSTED${NC}"
        fi
    done
    
    mapfile -t compose_files < <(find_docker_compose_files)
    echo -e "\n${BOLD}📁 Docker Compose Files:${NC} ${#compose_files[@]} found"
}

# Show help
show_help() {
    cat << EOF

🐳 Docker Network Subnet Manager - Help
======================================

This script provides comprehensive Docker network subnet management with the following features:

COMMANDS:
    --scan                     Scan existing Docker networks
    --find-subnet [SIZE]       Find next available subnet (default: /16)
    --update-compose FILE      Update docker-compose.yml with new network
    --generate-override FILE   Generate docker-compose.override.yml
    --report [FILE]           Generate comprehensive usage report
    --interactive             Run in interactive mode (recommended)
    --cleanup                 Clean up unused Docker networks

OPTIONS:
    --base-dir DIR            Base directory to scan (default: current)
    --subnet-size SIZE        Default subnet size: 16, 24, 25, 26 (default: 16)
    --network NAME            Network name for operations
    --dry-run                 Simulate changes without applying them
    --verbose                 Enable verbose logging
    --help                    Show this help message

EXAMPLES:

    # Interactive mode (recommended)
    $SCRIPT_NAME --interactive

    # Scan and show current usage
    $SCRIPT_NAME --scan

    # Find next available /24 subnet
    $SCRIPT_NAME --find-subnet 24

    # Update specific docker-compose.yml file
    $SCRIPT_NAME --update-compose ./docker-compose.yml --network mynetwork

    # Generate override file
    $SCRIPT_NAME --generate-override ./docker-compose.yml --network mynetwork

    # Generate detailed JSON report
    $SCRIPT_NAME --report subnet_analysis.json

    # Dry run mode (simulate changes)
    $SCRIPT_NAME --update-compose ./docker-compose.yml --network test --dry-run

SUBNET MANAGEMENT:
    - Manages subnets within 172.16.0.0/12 private range
    - Automatically detects conflicts with existing networks
    - Supports multiple subnet sizes (/16, /24, /25, /26)
    - Provides backup and rollback mechanisms
    - Handles subnet exhaustion with alternative solutions

REQUIREMENTS:
    - Docker (for network scanning)
    - yq (optional, for better YAML parsing)
    - jq (optional, for JSON processing)

For more information, visit: https://github.com/your-repo/docker-subnet-manager

EOF
}

# Main script logic
main() {
    local action=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive|-i)
                INTERACTIVE=true
                shift
                ;;
            --scan)
                action="scan"
                shift
                ;;
            --find-subnet)
                action="find_subnet"
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    SUBNET_SIZE="$2"
                    shift
                fi
                shift
                ;;
            --update-compose)
                action="update_compose"
                if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
                    COMPOSE_FILE="$2"
                    shift
                else
                    log_error "--update-compose requires a file path"
                    exit 1
                fi
                shift
                ;;
            --generate-override)
                action="generate_override"
                if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
                    COMPOSE_FILE="$2"
                    shift
                else
                    log_error "--generate-override requires a file path"
                    exit 1
                fi
                shift
                ;;
            --report)
                action="report"
                if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
                    REPORT_FILE="$2"
                    shift
                fi
                shift
                ;;
            --cleanup)
                action="cleanup"
                shift
                ;;
            --base-dir)
                if [[ -n "$2" ]]; then
                    BASE_DIR="$2"
                    shift
                else
                    log_error "--base-dir requires a directory path"
                    exit 1
                fi
                shift
                ;;
            --subnet-size)
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    SUBNET_SIZE="$2"
                    shift
                else
                    log_error "--subnet-size requires a numeric value"
                    exit 1
                fi
                shift
                ;;
            --network)
                if [[ -n "$2" ]]; then
                    NETWORK_NAME="$2"
                    shift
                else
                    log_error "--network requires a network name"
                    exit 1
                fi
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Initialize
    print_header "Docker Network Subnet Manager"
    log_info "Starting Docker Subnet Manager"
    log_info "Base directory: $BASE_DIR"
    log_info "Default subnet size: /$SUBNET_SIZE"
    log_info "Dry run mode: $DRY_RUN"
    
    # Check dependencies
    check_dependencies
    
    # Run requested action
    if [[ "$INTERACTIVE" == "true" ]]; then
        interactive_main_menu
    elif [[ -n "$action" ]]; then
        case $action in
            scan)
                scan_docker_networks
                ;;
            find_subnet)
                if subnet=$(find_next_available_subnet "$SUBNET_SIZE"); then
                    echo "Next available /$SUBNET_SIZE subnet: $subnet"
                else
                    log_error "No available subnets found"
                    handle_subnet_exhaustion "$SUBNET_SIZE"
                    exit 1
                fi
                ;;
            update_compose)
                if [[ -z "$NETWORK_NAME" ]]; then
                    log_error "--network is required for --update-compose"
                    exit 1
                fi
                if ! [[ -f "$COMPOSE_FILE" ]]; then
                    log_error "Compose file not found: $COMPOSE_FILE"
                    exit 1
                fi
                scan_docker_networks
                if subnet=$(find_next_available_subnet "$SUBNET_SIZE"); then
                    if update_compose_file "$COMPOSE_FILE" "$NETWORK_NAME" "$subnet"; then
                        log_info "Successfully updated $COMPOSE_FILE with network $NETWORK_NAME -> $subnet"
                    else
                        log_error "Failed to update compose file"
                        exit 1
                    fi
                else
                    log_error "No available subnets found"
                    exit 1
                fi
                ;;
            generate_override)
                if [[ -z "$NETWORK_NAME" ]]; then
                    log_error "--network is required for --generate-override"
                    exit 1
                fi
                if ! [[ -f "$COMPOSE_FILE" ]]; then
                    log_error "Compose file not found: $COMPOSE_FILE"
                    exit 1
                fi
                scan_docker_networks
                if subnet=$(find_next_available_subnet "$SUBNET_SIZE"); then
                    if override_file=$(generate_override_file "$COMPOSE_FILE" "$NETWORK_NAME" "$subnet"); then
                        log_info "Generated override file: $override_file"
                    else
                        log_error "Failed to generate override file"
                        exit 1
                    fi
                else
                    log_error "No available subnets found"
                    exit 1
                fi
                ;;
            report)
                generate_report "${REPORT_FILE:-subnet_report.json}"
                ;;
            cleanup)
                if check_docker; then
                    log_info "Cleaning up unused Docker networks..."
                    docker network prune -f
                    log_info "Network cleanup completed"
                else
                    log_error "Docker not available for cleanup"
                    exit 1
                fi
                ;;
        esac
    else
        # Default: show help and quick status
        show_help
        echo -e "\n${BOLD}Quick Status:${NC}"
        if check_docker; then
            scan_docker_networks
            if subnet=$(find_next_available_subnet "$SUBNET_SIZE" 2>/dev/null); then
                echo "Next available /$SUBNET_SIZE subnet: $subnet"
            else
                echo "⚠️  No available /$SUBNET_SIZE subnets found"
            fi
        else
            echo "⚠️  Docker not available"
        fi
        echo -e "\nRun with ${BOLD}--interactive${NC} for guided operations."
    fi
    
    log_info "Docker Subnet Manager completed"
}

# Trap to clean up on exit
trap 'echo -e "\n\n👋 Docker Subnet Manager exited"' EXIT

# Run main function
main "$@"