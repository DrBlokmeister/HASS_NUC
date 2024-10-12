from datetime import timedelta
import asyncio
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ssh_connection import SSHConnection
from .const import DOMAIN, CONF_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

class UnraidDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.connection = SSHConnection(
            entry.data["host"],
            entry.data.get("port"),
            entry.data["username"],
            entry.data.get("password"),
            entry.data.get("key"),
        )
        update_interval = timedelta(
            seconds=entry.options.get(CONF_POLL_INTERVAL, 30)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.data = {}

    async def _async_update_data(self):
        """Fetch data from NAS."""
        try:
            if not await self.connection.is_connected():
                await self.connection.connect()
                _LOGGER.debug("SSH connection established.")
            else:
                _LOGGER.debug("SSH connection already established.")

            # Fetch system metrics
            _LOGGER.debug("Fetching system metrics.")
            system_metrics = await self._fetch_system_metrics()
            _LOGGER.debug(f"System metrics: {system_metrics}")

            # Fetch Docker container stats
            _LOGGER.debug("Fetching Docker container stats.")
            container_stats = await self._fetch_container_stats()
            _LOGGER.debug(f"Container stats: {container_stats}")

            self.data = {**system_metrics, **container_stats}

            return self.data
        except Exception as err:
            _LOGGER.error(f"Error fetching data: {err}", exc_info=True)
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def _fetch_system_metrics(self):
        """Fetch system metrics via SSH."""
        commands = {
            "cpu_usage": "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'",
            "cpu_temperature": "sensors | grep 'CPU Temp:' | awk '{print $3}' | sed 's/+//g; s/°C//g'",
            "total_memory": "free -m | awk '/Mem:/ {print $2}'",
            "used_memory": "free -m | awk '/Mem:/ {print $3}'",
            "used_disk_space": "df -h | grep /mnt/user/ | awk '{print $3}' | sed 's/T//g' | awk '{print $1 * 1024}'",
            "nvme_composite_temperature": "sensors | grep 'Composite:' | awk '{print $2}' | sed 's/+//g; s/°C//g'",
            "parity_temperature": "smartctl -A /dev/sdb | grep Temperature_Celsius | awk '{print $10}'",
            "disk_1_temperature": "smartctl -A /dev/sdc | grep Temperature_Celsius | awk '{print \$10}'",
            "disk_2_temperature": "smartctl -A /dev/sde | grep Temperature_Celsius | awk '{print \$10}'",
            "disk_3_temperature": "smartctl -A /dev/sdd | grep Temperature_Celsius | awk '{print \$10}'",
            "dev_1_temperature": "smartctl -A /dev/sdg | grep Temperature_Celsius | awk '{print \$10}'",
            "dev_2_temperature": "smartctl -A /dev/sdf | grep Temperature_Celsius | awk '{print \$10}'",
            # Add more system metrics as needed
        }

        results = {}
        for key, cmd in commands.items():
            output = await self.connection.run_command(cmd)
            _LOGGER.debug(f"Command output for {key}: {output}")
            results[key] = self._parse_output(output)

        # Unraid array status
        array_status_cmd = "mdcmd status | grep 'mdState=' | cut -d'=' -f2 | awk '{print $1}'"
        array_status = await self.connection.run_command(array_status_cmd)
        _LOGGER.debug(f"Array status output: {array_status}")
        results["unraid_array_status"] = array_status.strip() == "STARTED"

        # Wireguard service status
        wireguard_status_cmd = "wg"
        wireguard_status = await self.connection.run_command(wireguard_status_cmd)
        _LOGGER.debug(f"Wireguard status output: {wireguard_status}")
        results["wireguard_service_status"] = bool(wireguard_status.strip())

        return results

    async def _fetch_container_stats(self):
        """Fetch Docker container stats via SSH."""
        container_list_cmd = "docker ps --format '{{.Names}}'"
        containers_output = await self.connection.run_command(container_list_cmd)
        _LOGGER.debug(f"Containers output: {containers_output}")
        containers = containers_output.strip().splitlines()

        results = {}
        for container in containers:
            # Container state
            state_cmd = f"docker inspect -f '{{{{.State.Running}}}}' {container}"
            state_output = await self.connection.run_command(state_cmd)
            is_running = state_output.strip() == "true"
            results[f"{container}_container_state"] = is_running
            _LOGGER.debug(f"Container {container} running: {is_running}")

            if is_running:
                # Container stats
                stats_cmd = f"docker stats --no-stream --format '{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.MemPerc}}}}' {container}"
                stats_output = await self.connection.run_command(stats_cmd)
                _LOGGER.debug(f"Stats output for {container}: {stats_output}")
                if stats_output:
                    try:
                        cpu_perc, mem_usage, mem_perc = stats_output.strip().split('|')
                        cpu_perc = cpu_perc.strip().strip('%')
                        mem_perc = mem_perc.strip().strip('%')

                        # Process mem_usage to extract used memory
                        mem_usage_used = mem_usage.split(' / ')[0].strip()

                        results[f"{container}_cpu_usage"] = float(cpu_perc)
                        results[f"{container}_mem_usage"] = mem_usage_used
                        results[f"{container}_mem_perc"] = float(mem_perc)
                    except ValueError as e:
                        _LOGGER.error(f"Error parsing stats for container {container}: {e}")
                        results[f"{container}_cpu_usage"] = 0.0
                        results[f"{container}_mem_usage"] = "0B"
                        results[f"{container}_mem_perc"] = 0.0
                else:
                    results[f"{container}_cpu_usage"] = 0.0
                    results[f"{container}_mem_usage"] = "0B"
                    results[f"{container}_mem_perc"] = 0.0
            else:
                # Container is not running
                results[f"{container}_cpu_usage"] = 0.0
                results[f"{container}_mem_usage"] = "0B"
                results[f"{container}_mem_perc"] = 0.0

        return results

    def _parse_output(self, output):
        """Parse command output to appropriate data type."""
        output = output.strip()
        if not output:
            return None
        try:
            if '.' in output:
                return float(output)
            else:
                return int(output)
        except ValueError:
            return output

    async def async_disconnect(self):
        """Disconnect the SSH session."""
        await self.connection.disconnect()
        _LOGGER.info("SSH connection disconnected.")
