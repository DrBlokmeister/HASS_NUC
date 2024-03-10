#!/bin/bash

# SSH key and NAS details
SSH_KEY="/config/.ssh/NUC_id_rsa"
NAS_USER="root"
NAS_IP="10.0.0.250"
OUTPUT_FILE="/config/www/nas_status.json"

# Check if the output file exists, if not create a default one
if [ ! -f "$OUTPUT_FILE" ]; then
  echo "{\"nas_available\": false}" > $OUTPUT_FILE
fi

# SSH command prefix
SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -q $NAS_USER@$NAS_IP"

# Function to update JSON value
update_json() {
    jq ".$1 = $2" $OUTPUT_FILE > temp.json && mv temp.json $OUTPUT_FILE
}

# Update last updated time in timestamp format
LAST_UPDATED=$(date "+%Y-%m-%dT%H:%M:%S%z")
update_json "last_updated" "\"$LAST_UPDATED\""

# Check NAS availability
if ! $SSH_CMD "exit" ; then
  update_json "nas_available" "false"
  exit 1
else
  update_json "nas_available" "true"
fi

# NAS CPU Usage
CPU_USAGE=$($SSH_CMD "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\\1/' | awk '{print 100 - \$1}'")
update_json "cpu_usage" "$CPU_USAGE"

# NAS CPU Temperature
CPU_TEMP=$($SSH_CMD "sensors | grep 'CPU Temp:' | awk '{print \$3}' | sed 's/+//g; s/°C//g'")
update_json "cpu_temperature" "$CPU_TEMP"

# NAS Total Memory
TOTAL_MEM=$($SSH_CMD "free -m | awk '/Mem:/ {print \$2}'")
update_json "total_memory" "$TOTAL_MEM"

# NAS Used Memory
USED_MEM=$($SSH_CMD "free -m | awk '/Mem:/ {print \$3}'")
update_json "used_memory" "$USED_MEM"

# NAS Used Disk Space (assuming in TB, converting to GB for consistency)
USED_DISK=$($SSH_CMD "df -h | grep /mnt/user/ | awk '{print \$3}' | sed 's/T//g' | awk '{print \$1 * 1024}'")
update_json "used_disk_space" "$USED_DISK"

# NAS NVMe Composite Temperature
NVME_TEMP=$($SSH_CMD "sensors | grep 'Composite:' | awk '{print \$2}' | sed 's/+//g; s/°C//g'")
update_json "nvme_composite_temperature" "$NVME_TEMP"

# Disk Temperatures
update_disk_temp() {
    local disk="$1"
    local name="$2"
    local temp=$($SSH_CMD "smartctl -A /dev/$disk | grep Temperature_Celsius | awk '{print \$10}'")
    update_json "$name" "$temp"
}

update_disk_temp "sdb" "parity_temperature"
update_disk_temp "sdc" "disk_1_temperature"
update_disk_temp "sdd" "disk_3_temperature"
update_disk_temp "sde" "disk_2_temperature"
update_disk_temp "sdf" "dev_2_temperature"
update_disk_temp "sdg" "dev_1_temperature"
