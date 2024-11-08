#!/bin/bash

#Enable for troubleshooting purposes
#set -x

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
    # Use the alternative syntax for property names that might contain special characters
    jq ".[\"$1\"] = $2" $OUTPUT_FILE > temp.json && mv temp.json $OUTPUT_FILE
}

# Assume NAS is unavailable initially
nas_available=false

# Update last updated time in timestamp format
LAST_UPDATED=$(date "+%Y-%m-%dT%H:%M:%S%z")
update_json "last_updated" "\"$LAST_UPDATED\""

# Consolidate all metrics into one SSH call
ALL_METRICS=$($SSH_CMD "
    echo cpu_usage \$(top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\\1/' | awk '{print 100 - \$1}');
    echo cpu_temperature \$(sensors | grep 'CPU Temp:' | awk '{print \$3}' | sed 's/+//g; s/°C//g');
    free -m | awk '/Mem:/ {print \"total_memory \"\$2\"\\nused_memory \"\$3}';
    echo used_disk_space \$(df -h | grep /mnt/user/ | awk '{print \$3}' | sed 's/T//g' | awk '{print \$1 * 1024}');
    echo link_speed \$(ethtool eth0 | grep 'Speed:' | awk '{print \$2}');
    echo nvme_composite_temperature \$(sensors | grep 'Composite:' | awk '{print \$2}' | sed 's/+//g; s/°C//g');
    
    # Function to safely get disk temperature or set to null if unavailable
    get_disk_temp() {
        local disk_name=\$1
        local disk_device=\$2
        temp=\$(smartctl -n standby -A \$disk_device | grep Temperature_Celsius | awk '{print \$10}')
        if [[ -z "\$temp" ]]; then
            echo \"\${disk_name}_temperature null\"
        else
            echo \"\${disk_name}_temperature \$temp\"
        fi
    }

    # Get temperatures for parity and disks
    get_disk_temp parity /dev/sdb
    get_disk_temp disk_1 /dev/sdc
    get_disk_temp disk_2 /dev/sde
    get_disk_temp disk_3 /dev/sdd
    get_disk_temp dev_1 /dev/sdg
    get_disk_temp dev_2 /dev/sdf

    for container in transmission plex Firefox ApacheGuacamole PhotoPrism Onedrive HDDTemp glances ntp swag; do
        # Check if the container exists
        if docker inspect -f '{{.State.Running}}' \$container > /dev/null 2>&1; then
            state=\$(docker inspect -f '{{.State.Running}}' \$container)
            echo \${container}_container_state \$(if [ \"\$state\" = \"true\" ]; then echo true; else echo false; fi)
            
            # Fetch container stats
            stats=\$(docker stats --no-stream --format \"{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.MemPerc}}\" \$container)
            cpu_usage=\$(echo \$stats | awk '{print \$2}' | sed 's/%//') # CPU usage without the percent sign
            mem_usage=\$(echo \$stats | awk '{print \$3}') # Memory usage (used)
            mem_perc=\$(echo \$stats | awk '{print \$NF}' | sed 's/%//') # Memory usage percent without the percent sign, assuming it's the last field (NF: Number of Fields)
            
            echo \${container}_cpu_usage \$cpu_usage
            echo \${container}_mem_usage \$mem_usage
            echo \${container}_mem_perc \$mem_perc
        else
            # Container does not exist, set state to false and metrics to null
            echo \${container}_container_state false
            echo \${container}_cpu_usage 0
            echo \${container}_mem_usage 0B
            echo \${container}_mem_perc 0.00
        fi
    done
    echo unraid_array_status \$(mdcmd status | grep 'mdState=' | cut -d'=' -f2 | awk '{print \$1 == \"STARTED\" ? \"true\" : \"false\"}');
    echo wireguard_service_status \$(if [[ \$(wg) ]]; then echo true; else echo false; fi);
")

# Check if SSH command was successful
if [ $? -ne 0 ]; then
    # SSH command failed, NAS is likely unavailable
    update_json "nas_available" "false"
else
    # Update nas_available based on metric retrieval outcome
    update_json "nas_available" "true"
    # Parse ALL_METRICS and update JSON, ensuring numeric values are correctly handled
    echo "$ALL_METRICS" | while read -r line; do
        key=$(echo "$line" | awk '{print $1}')
        value=$(echo "$line" | cut -d' ' -f2-)

        # Directly check for boolean values
        if [[ "$value" == "true" || "$value" == "false" ]]; then
            update_json "$key" "$value"
        else
            # Attempt to determine if the value is an integer or float
            if [[ "$value" =~ ^-?[0-9]+$ ]] || [[ "$value" =~ ^-?[0-9]+\.[0-9]+$ ]]; then
                update_json "$key" "$value"  # Quotes ensure proper numeric handling
                # Since we're successfully parsing metrics, set NAS as available
                nas_available=true
            else
                # It's a string or null, update accordingly
                if [[ "$value" == "null" ]]; then
                    update_json "$key" -1  # No quotes to set JSON null
                else
                    update_json "$key" "\"$value\""
                fi
            fi
        fi
    done
fi
