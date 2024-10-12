import asyncssh
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class SSHConnection:
    def __init__(self, host, port, username, password=None, key=None):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._key = key
        self._conn = None

    async def connect(self):
        """Establish an SSH connection if not already connected."""
        # Only connect if we aren't already connected
        if self._conn is not None:
            _LOGGER.debug(f"Already connected to {self._host}")
            return

        conn_params = {
            "host": self._host,
            "port": self._port,
            "username": self._username,
            "known_hosts": None,  # Disable known_hosts checking
        }
        if self._password:
            conn_params["password"] = self._password
        if self._key:
            conn_params["client_keys"] = [asyncssh.import_private_key(self._key)]
        else:
            conn_params["client_keys"] = None  # Use default keys

        try:
            self._conn = await asyncssh.connect(**conn_params)
            _LOGGER.info(f"Connected to {self._host}")
        except Exception as e:
            _LOGGER.error(f"Failed to connect to {self._host}: {e}")
            self._conn = None
            raise

    async def disconnect(self):
        """Close the SSH connection if it exists."""
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
            _LOGGER.info(f"Disconnected from {self._host}")

    async def run_command(self, command):
        """Run a command over SSH, reconnecting if necessary."""
        try:
            # Check if the connection is active
            if self._conn is None:
                await self.connect()

            # Run the command
            result = await self._conn.run(command)
            return result.stdout
        except (asyncssh.ConnectionLost, asyncssh.DisconnectError) as e:
            _LOGGER.warning(f"Connection lost while running command '{command}': {e}")
            # Attempt to reconnect and retry the command
            await self.disconnect()  # Ensure any remaining connection is closed
            await self.connect()
            result = await self._conn.run(command)
            return result.stdout
        except Exception as e:
            _LOGGER.error(f"Error running command '{command}': {e}")
            raise

    async def is_connected(self):
        """Check if the SSH connection is active."""
        return self._conn is not None
