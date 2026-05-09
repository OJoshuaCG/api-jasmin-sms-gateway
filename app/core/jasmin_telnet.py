import asyncio
import time
from asyncio import StreamReader, StreamWriter
from typing import Optional

from app.core.logger import get_logger

logger = get_logger(__name__)

# Jasmin jcli prompts — Jasmin 0.11.x uses "jcli : " as main prompt.
# The main prompt always appears after every command completes.
# The interactive sub-prompt appears when jcli waits for field input.
_MAIN_PROMPT = "jcli : "

# Some Jasmin builds use "> " (single >) others use ">> " (double >).
# Both are listed. Detection relies on endswith() sorted by length (longest first),
# so "jcli : " is always checked before "> " — preventing the "> " ⊂ "jcli : " ambiguity.
_INTERACTIVE_PROMPTS = [">> ", "> "]

# All prompts sorted longest-first for safe endswith detection
_ALL_PROMPTS: list[str] = sorted(
    [_MAIN_PROMPT] + _INTERACTIVE_PROMPTS, key=len, reverse=True
)

_USERNAME_PROMPT = "Username: "
_PASSWORD_PROMPT = "Password: "


class TelnetNotConnectedError(Exception):
    pass


class JasminTelnetSession:
    """
    Persistent Telnet session to Jasmin's jcli. Singleton per process.
    All commands are serialized via asyncio.Lock (jcli is not concurrent).
    Auto-reconnects with exponential backoff (1s → 2s → 4s → max 30s).
    persist() is called automatically after every write operation.
    """

    _instance: Optional["JasminTelnetSession"] = None

    def __init__(self, host: str, port: int, user: str, password: str, timeout: int = 10):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._timeout = timeout

        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._reconnecting = False
        self._connected_at: Optional[float] = None
        self._reconnect_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    @classmethod
    def get_instance(cls) -> "JasminTelnetSession":
        if cls._instance is None:
            raise RuntimeError("JasminTelnetSession not initialized")
        return cls._instance

    @classmethod
    async def init(
        cls,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout: int = 10,
    ) -> "JasminTelnetSession":
        cls._instance = cls(host, port, user, password, timeout)
        await cls._instance.connect()
        return cls._instance

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_reconnecting(self) -> bool:
        return self._reconnecting

    @property
    def uptime_seconds(self) -> Optional[float]:
        if self._connected and self._connected_at:
            return round(time.time() - self._connected_at, 1)
        return None

    async def connect(self) -> None:
        logger.info("Connecting to Jasmin jcli at %s:%s", self._host, self._port)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            # Offer TTYPE proactively — real telnet clients do this, and Jasmin's
            # Twisted server uses the DONT TTYPE exchange to complete negotiation
            # before sending the Username prompt.
            writer.write(b"\xff\xfb\x18")  # IAC WILL TTYPE
            await writer.drain()
            await self._telnet_read_until(reader, writer, _USERNAME_PROMPT.encode())
            writer.write((self._user + "\r\n").encode())
            await writer.drain()
            await self._telnet_read_until(reader, writer, _PASSWORD_PROMPT.encode())
            writer.write((self._password + "\r\n").encode())
            await writer.drain()
            welcome = await self._telnet_read_until(reader, writer, _MAIN_PROMPT.encode())
            if b"Authentication failure" in welcome or b"Login incorrect" in welcome:
                writer.close()
                raise ConnectionError("jcli authentication failed — check JASMIN_TELNET_USER/PASSWORD")
            self._reader = reader
            self._writer = writer
            self._connected = True
            self._reconnecting = False
            self._connected_at = time.time()
            logger.info("Connected to Jasmin jcli")
        except Exception as exc:
            self._connected = False
            logger.error("Failed to connect to Jasmin jcli: %s: %s", type(exc).__name__, exc)
            raise

    async def disconnect(self) -> None:
        self._connected = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        logger.info("Disconnected from Jasmin jcli")

    # ------------------------------------------------------------------ #
    #  Internal I/O helpers
    # ------------------------------------------------------------------ #

    async def _telnet_read_until(
        self, reader: StreamReader, writer: StreamWriter, delimiter: bytes
    ) -> bytes:
        """
        Read from the Telnet stream handling IAC sequences on the fly, until
        the accumulated non-IAC text ends with `delimiter`.

        Jasmin's negotiation spans multiple rounds (server sends options, we
        respond, server sends more options in reply, we respond again, and only
        then sends the prompt). A single up-front negotiation phase is not enough.

        IAC DO X   (FF FD X) → WONT X, except SGA (03) → WILL SGA (full-duplex)
        IAC WILL X (FF FB X) → DO X
        IAC DONT X (FF FE X) → WONT X
        IAC WONT X (FF FC X) → DONT X
        IAC SB...SE          → skipped (variable-length subnegotiation)
        """
        text = b""
        while not text.endswith(delimiter):
            chunk = await asyncio.wait_for(reader.read(4096), timeout=self._timeout)
            if not chunk:
                raise ConnectionError("Connection closed by server")
            iac_response = bytearray()
            i = 0
            while i < len(chunk):
                if chunk[i] == 0xFF and i + 1 < len(chunk):
                    cmd = chunk[i + 1]
                    if cmd == 0xFA:  # SB: skip to IAC SE (FF F0)
                        i += 2
                        while i < len(chunk) - 1:
                            if chunk[i] == 0xFF and chunk[i + 1] == 0xF0:
                                i += 2
                                break
                            i += 1
                    elif i + 2 < len(chunk):
                        opt = chunk[i + 2]
                        if cmd == 0xFD:    # DO
                            if opt == 0x03: iac_response += bytes([0xFF, 0xFB, opt])  # SGA → WILL
                            else:           iac_response += bytes([0xFF, 0xFC, opt])  # rest → WONT
                        elif cmd == 0xFB:  # WILL → DO
                            iac_response += bytes([0xFF, 0xFD, opt])
                        elif cmd == 0xFE:  # DONT → WONT
                            iac_response += bytes([0xFF, 0xFC, opt])
                        elif cmd == 0xFC:  # WONT → DONT
                            iac_response += bytes([0xFF, 0xFE, opt])
                        i += 3
                    else:
                        i += 1
                else:
                    text += bytes([chunk[i]])
                    i += 1
            if iac_response:
                writer.write(bytes(iac_response))
                await writer.drain()
        return text

    async def _read_raw_until(self, reader: StreamReader, delimiter: bytes) -> bytes:
        """
        Read from *reader* into a buffer until the buffer ends with *delimiter*.
        Guaranteed no data loss — the buffer is always a contiguous prefix of
        what the server sent; nothing after the delimiter is consumed.
        """
        buf = b""
        while not buf.endswith(delimiter):
            chunk = await asyncio.wait_for(reader.read(1024), timeout=self._timeout)
            if not chunk:
                raise ConnectionError("Connection closed by server")
            buf += chunk
        return buf

    async def _read_until(self, delimiter: str) -> str:
        """Read until delimiter (str). Returns everything including the delimiter."""
        raw = await self._read_raw_until(self._reader, delimiter.encode())
        return raw.decode("utf-8", errors="replace")

    async def _read_until_one_of(self, delimiters: list[str]) -> tuple[str, str]:
        """
        Read until the accumulated buffer ENDS WITH one of the given delimiters.
        Delimiters are checked longest-first to resolve substring ambiguities
        (e.g. "> " is a suffix of "jcli> " — checking "jcli> " first avoids
        a false positive interactive-mode detection on the main prompt).

        Returns (content_before_delimiter, matched_delimiter).
        No bytes are ever consumed beyond the matching delimiter.
        """
        sorted_delims = sorted(delimiters, key=len, reverse=True)
        buf = ""
        while True:
            try:
                chunk = await asyncio.wait_for(self._reader.read(256), timeout=self._timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(
                    f"Timeout ({self._timeout}s) waiting for jcli response. "
                    "Expected one of: " + repr(delimiters)
                )
            if not chunk:
                raise ConnectionError("Connection closed while waiting for jcli response")
            buf += chunk.decode("utf-8", errors="replace")
            for d in sorted_delims:
                if buf.endswith(d):
                    # Strip the delimiter from the content before returning
                    return buf[: -len(d)].strip(), d

    def _strip_prompt(self, response: str) -> str:
        """Remove trailing jcli prompt and surrounding whitespace from a response."""
        return response.removesuffix(_MAIN_PROMPT).strip()

    def _is_interactive_match(self, matched: str) -> bool:
        return matched in _INTERACTIVE_PROMPTS

    # ------------------------------------------------------------------ #
    #  Command execution
    # ------------------------------------------------------------------ #

    def _handle_io_error(self, exc: Exception) -> None:
        """Mark disconnected, schedule reconnect, then raise TelnetNotConnectedError."""
        self._connected = False
        if not self._reconnecting:
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        raise TelnetNotConnectedError(f"Jasmin jcli connection error: {exc}")

    async def execute(self, command: str, persist: bool = False) -> str:
        """
        Execute a simple (non-interactive) jcli command.
        Returns the response text with the trailing prompt stripped.
        If persist=True, runs 'persist' immediately after.
        """
        async with self._lock:
            if not self._connected:
                raise TelnetNotConnectedError("Jasmin jcli is not connected")
            try:
                self._writer.write((command + "\r\n").encode())
                await self._writer.drain()
                response = await self._read_until(_MAIN_PROMPT)
                response = self._strip_prompt(response)
                if persist:
                    await self._persist_unlocked()
                return response
            except TelnetNotConnectedError:
                raise
            except (ConnectionError, asyncio.TimeoutError, OSError) as exc:
                self._handle_io_error(exc)

    async def execute_interactive(
        self,
        command: str,
        fields: list[tuple[str, str]],
        persist: bool = True,
    ) -> str:
        """
        Execute an interactive jcli command (--add, --update).

        Flow:
          1. Send command → wait for "> " or ">> " (interactive) or "jcli> " (error/no-interactive)
          2. If non-interactive (main prompt returned): return the response immediately
          3. For each field: send "key value\\r\\n" → wait for next prompt
          4. Send "ok\\r\\n" → wait for "jcli> " (final result)
          5. If persist=True: execute 'persist'
        """
        async with self._lock:
            if not self._connected:
                raise TelnetNotConnectedError("Jasmin jcli is not connected")
            try:
                self._writer.write((command + "\r\n").encode())
                await self._writer.drain()

                content, matched = await self._read_until_one_of(_ALL_PROMPTS)

                # Command returned to main prompt immediately — either an error
                # or a non-interactive command (e.g. group --add)
                if not self._is_interactive_match(matched):
                    return content.strip()

                # Interactive mode: send each field assignment
                for key, value in fields:
                    self._writer.write(f"{key} {value}\r\n".encode())
                    await self._writer.drain()
                    _content, next_match = await self._read_until_one_of(_ALL_PROMPTS)
                    # If jcli exited interactive mode early (validation error, etc.)
                    if not self._is_interactive_match(next_match):
                        return _content.strip()

                # Confirm and collect final result
                self._writer.write(b"ok\r\n")
                await self._writer.drain()
                response = await self._read_until(_MAIN_PROMPT)
                response = self._strip_prompt(response)

                if persist:
                    await self._persist_unlocked()
                return response
            except TelnetNotConnectedError:
                raise
            except (ConnectionError, asyncio.TimeoutError, OSError) as exc:
                self._handle_io_error(exc)

    async def _persist_unlocked(self) -> None:
        """
        Execute 'persist'. MUST be called while self._lock is held.
        Jasmin writes all in-memory config to disk; errors here mean the
        operation is considered failed — the caller should propagate the error.
        """
        self._writer.write(b"persist\r\n")
        await self._writer.drain()
        response = await self._read_until(_MAIN_PROMPT)
        response_lower = response.lower()
        if (
            "persistence storage updated" not in response_lower
            and "success" not in response_lower
            and "updated" not in response_lower
        ):
            raise RuntimeError(f"persist failed: {self._strip_prompt(response)}")

    async def persist(self) -> str:
        """Execute 'persist' explicitly (acquires lock)."""
        async with self._lock:
            if not self._connected:
                raise TelnetNotConnectedError("Jasmin jcli is not connected")
            try:
                await self._persist_unlocked()
                return "Persistence storage updated"
            except TelnetNotConnectedError:
                raise
            except (ConnectionError, asyncio.TimeoutError, OSError) as exc:
                self._handle_io_error(exc)

    # ------------------------------------------------------------------ #
    #  Reconnection
    # ------------------------------------------------------------------ #

    async def _reconnect_loop(self) -> None:
        self._reconnecting = True
        delay = 1
        while not self._connected:
            logger.info("Reconnecting to Jasmin jcli in %ss…", delay)
            await asyncio.sleep(delay)
            try:
                await self.connect()
                logger.info("Successfully reconnected to Jasmin jcli")
                self._reconnecting = False
                return
            except Exception as exc:
                logger.error("Reconnect attempt failed: %s: %s", type(exc).__name__, exc)
                delay = min(delay * 2, 30)

    async def force_reconnect(self) -> None:
        """Immediately close and reopen the Telnet connection."""
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
        self._connected = False
        await self.connect()

    async def session_info(self) -> dict:
        return {
            "connected": self._connected,
            "reconnecting": self._reconnecting,
            "uptime_seconds": self.uptime_seconds,
            "host": self._host,
            "port": self._port,
        }
