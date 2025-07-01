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
    echo link_speed \$(ethtool eth0 | grep 'Speed:' | awk '{print \$2}');
    echo nvme_composite_temperature \$(sensors | grep 'Composite:' | awk '{print \$2}' | sed 's/+//g; s/°C//g');
    
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
