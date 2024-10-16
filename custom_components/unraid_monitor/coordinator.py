from datetime import datetime, timedelta
import asyncio
import logging
import re

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
                _LOGGER.info("New SSH connection established.")
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
        # Basic system commands
        commands = {
            "cpu_usage": "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'",
            "cpu_temperature": "sensors | grep 'CPU Temp:' | awk '{print $3}' | sed 's/+//g; s/°C//g'",
            "total_memory": "free -m | awk '/Mem:/ {print $2}'",
            "used_memory": "free -m | awk '/Mem:/ {print $3}'",
            "used_disk_space": "df -h | grep /mnt/user/ | awk '{print $3}' | sed 's/T//g' | awk '{print $1 * 1024}'",
            "nvme_composite_temperature": "sensors | grep 'Composite:' | awk '{print $2}' | sed 's/+//g; s/°C//g'"
        }

        results = {}
        for key, cmd in commands.items():
            output = await self.connection.run_command(cmd)
            _LOGGER.debug(f"Command output for {key}: {output}")
            results[key] = self._parse_output(output)

        # Dynamically check for available disks and fetch temperatures
        disk_list_cmd = "ls /dev/sd* | grep -o '/dev/sd[a-z]' | sort -u"
        disk_list_output = await self.connection.run_command(disk_list_cmd)
        _LOGGER.debug(f"Disk list output: {disk_list_output}")

        if disk_list_output:
            disks = disk_list_output.strip().splitlines()
            for disk in disks:
                temperature_cmd = f"smartctl -A {disk} | grep Temperature_Celsius | awk '{{print $10}}'"
                temperature_output = await self.connection.run_command(temperature_cmd)
                if temperature_output:
                    disk_temp_key = f"{disk.split('/')[-1]}_temperature"
                    results[disk_temp_key] = self._parse_output(temperature_output)
                    _LOGGER.debug(f"Temperature for {disk}: {temperature_output.strip()}")

        # Unraid array status
        array_status_cmd = "mdcmd status | grep 'mdState=' | cut -d'=' -f2 | awk '{print $1}'"
        array_status = await self.connection.run_command(array_status_cmd)
        _LOGGER.debug(f"Array status output: {array_status}")
        results["unraid_array_status"] = array_status.strip() == "STARTED"

        # Dynamically handle WireGuard interfaces
        wireguard_status_cmd = "wg"
        wireguard_status = await self.connection.run_command(wireguard_status_cmd)
        _LOGGER.debug(f"Wireguard status output: {wireguard_status}")

        # Parse WireGuard output with regular expressions
        interfaces = re.findall(r"interface: (wg\d+)", wireguard_status)
        peers = re.findall(
            r"peer: ([A-Za-z0-9+/=]+)\n\s*endpoint: ([\d.]+:\d+).*\n\s*latest handshake: (\d+) seconds ago\n\s*transfer: ([\d.]+ \w+) received, ([\d.]+ \w+)",
            wireguard_status
        )
        current_time = datetime.now()

        for i, interface in enumerate(interfaces):
            if i < len(peers):
                peer_key, endpoint, latest_handshake, transfer_rx, transfer_tx = peers[i]

                # Convert latest handshake to timestamp
                handshake_timestamp = current_time - timedelta(seconds=int(latest_handshake))
                results[f"{interface}_endpoint"] = endpoint
                results[f"{interface}_latest_handshake"] = handshake_timestamp.isoformat()
                results[f"{interface}_received"] = self._parse_data_size(transfer_rx)
                results[f"{interface}_sent"] = self._parse_data_size(transfer_tx)

                _LOGGER.debug(f"WireGuard {interface} - Endpoint: {endpoint}, "
                            f"Handshake: {handshake_timestamp.isoformat()}, "
                            f"Received: {transfer_rx}, Sent: {transfer_tx}")

        return results

    def _parse_data_size(self, data):
        """Convert data size string to a consistent unit (KiB)."""
        size, unit = data.split()
        size = float(size)
        if unit == "GiB":
            return size * 1024 * 1024
        elif unit == "MiB":
            return size * 1024
        elif unit == "KiB":
            return size
        elif unit == "B":
            return size / 1024
        return size

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

    async def start_container(self, container_name):
        """Start a Docker container."""
        try:
            start_cmd = f"docker start {container_name}"
            await self.connection.run_command(start_cmd)
            _LOGGER.info(f"Started container {container_name}")
            # Perform fast polling to update state quickly
            await self._fast_polling()
        except Exception as e:
            _LOGGER.error(f"Error starting container {container_name}: {e}")

    async def stop_container(self, container_name):
        """Stop a Docker container."""
        try:
            stop_cmd = f"docker stop {container_name}"
            await self.connection.run_command(stop_cmd)
            _LOGGER.info(f"Stopped container {container_name}")
            # Perform fast polling to update state quickly
            await self._fast_polling()
        except Exception as e:
            _LOGGER.error(f"Error stopping container {container_name}: {e}")

    async def _fast_polling(self):
        """Perform fast polling to update state quickly after an action."""
        original_interval = self.update_interval
        self.update_interval = timedelta(seconds=5)  # Set fast polling interval
        for _ in range(3):  # Poll 3 times at 5-second intervals
            await self.async_request_refresh()
            await asyncio.sleep(5)
        self.update_interval = original_interval  # Restore original polling interval

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
