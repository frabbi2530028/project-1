"""Small LAN multiplayer helper for Neon Drift.

The host is authoritative for room membership and the shared maze seed. Clients
send lightweight player state and receive everybody else's state back.
"""

from __future__ import annotations

import errno
import json
import socket
import threading
import time
from dataclasses import dataclass, field


MULTIPLAYER_PORT = 50123
DISCOVERY_PORT = 50124
MULTIPLAYER_MAX_PLAYERS = 3
ROOM_DISCOVERY_MAGIC = "NEON_DRIFT_LAN_ROOM"


def _is_joinable_ipv4(ip: str) -> bool:
    return bool(ip) and not ip.startswith("127.") and not ip.startswith("169.254.")


def _remember_ip(ips: list[str], ip: str) -> None:
    if _is_joinable_ipv4(ip) and ip not in ips:
        ips.append(ip)


def local_room_codes() -> list[str]:
    """Return possible same-Wi-Fi join codes for every useful local interface."""
    ips: list[str] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            _remember_ip(ips, sock.getsockname()[0])
        finally:
            sock.close()
    except OSError:
        pass

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            _remember_ip(ips, ip)
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            _remember_ip(ips, info[4][0])
    except OSError:
        pass

    return ips


def local_room_code() -> str:
    """Return a join code that works on the same Wi-Fi/hotspot."""
    codes = local_room_codes()
    return codes[0] if codes else "127.0.0.1"


def normalize_room_code(code: str) -> str:
    """Accept either a normal IP address or digits-only room code."""
    code = (code or "").strip()
    if "." in code:
        return code
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) == 12:
        return ".".join(str(int(digits[i:i + 3])) for i in range(0, 12, 3))
    return code


def compact_room_code(ip: str) -> str:
    """Display a numeric fallback for players who prefer not to type dots."""
    try:
        parts = [int(part) for part in ip.split(".")]
        if len(parts) == 4 and all(0 <= part <= 255 for part in parts):
            return "".join(f"{part:03d}" for part in parts)
    except ValueError:
        pass
    return ip


def format_join_error(exc: BaseException, host_code: str = "") -> str:
    """Convert raw socket errors into player-friendly lobby messages."""
    error_no = getattr(exc, "errno", None)
    unreachable_errors = {
        getattr(errno, "ENETUNREACH", -1),
        getattr(errno, "EHOSTUNREACH", -1),
        getattr(errno, "EHOSTDOWN", -1),
        65,
    }
    if isinstance(exc, socket.timeout):
        return "JOIN FAILED: CONNECTION TIMED OUT"
    if isinstance(exc, ConnectionRefusedError):
        return "JOIN FAILED: ROOM NOT OPEN ON THAT CODE"
    if error_no in unreachable_errors:
        return "JOIN FAILED: HOST NOT REACHABLE - USE AUTO-FIND"
    if isinstance(exc, socket.gaierror):
        return "JOIN FAILED: BAD ROOM CODE"
    detail = str(exc).strip()
    if host_code:
        return f"JOIN FAILED: CHECK CODE {host_code}"
    return f"JOIN FAILED: {detail}" if detail else "JOIN FAILED"


def _udp_reply_ip(peer_ip: str) -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((peer_ip, DISCOVERY_PORT))
            ip = sock.getsockname()[0]
            if _is_joinable_ipv4(ip):
                return ip
        finally:
            sock.close()
    except OSError:
        pass
    return local_room_code()


def _decode_discovery(data: bytes) -> dict | None:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if payload.get("magic") != ROOM_DISCOVERY_MAGIC:
        return None
    return payload


def discover_lan_room(timeout: float = 1.5) -> str | None:
    """Find a host lobby on the same Wi-Fi/hotspot using UDP broadcast."""
    deadline = time.time() + max(0.1, timeout)
    request = json.dumps({
        "magic": ROOM_DISCOVERY_MAGIC,
        "type": "discover",
        "tcp_port": MULTIPLAYER_PORT,
    }, separators=(",", ":")).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.18)
        targets = [("255.255.255.255", DISCOVERY_PORT)]
        for ip in local_room_codes():
            parts = ip.split(".")
            if len(parts) == 4:
                targets.append((".".join(parts[:3] + ["255"]), DISCOVERY_PORT))
        while time.time() < deadline:
            for target in targets:
                try:
                    sock.sendto(request, target)
                except OSError:
                    continue
            wait_until = min(deadline, time.time() + 0.2)
            while time.time() < wait_until:
                try:
                    data, addr = sock.recvfrom(2048)
                except socket.timeout:
                    break
                except OSError:
                    return None
                payload = _decode_discovery(data)
                if not payload or payload.get("type") != "offer":
                    continue
                host = normalize_room_code(str(payload.get("host") or addr[0]))
                if host:
                    return host
    finally:
        try:
            sock.close()
        except OSError:
            pass
    return None


def _send_json(sock: socket.socket, payload: dict) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
    sock.sendall(data)


class JsonSocketReader:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b""

    def recv(self) -> dict | None:
        while b"\n" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        if not line.strip():
            return {}
        return json.loads(line.decode("utf-8"))


@dataclass
class RemotePlayerState:
    player_id: int
    name: str = ""
    ship: int = 0
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0
    health: float = 100.0
    max_health: float = 100.0
    connected: bool = True
    last_seen: float = field(default_factory=time.time)


class MultiplayerHost:
    def __init__(self, room_code: str, preset_key: str, maze_seed: int, max_players: int = MULTIPLAYER_MAX_PLAYERS):
        self.room_code = room_code
        self.preset_key = preset_key
        self.maze_seed = maze_seed
        self.max_players = max_players
        self.player_id = 1
        self.players: dict[int, RemotePlayerState] = {}
        self.maze_state: dict | None = None
        self.incoming_events: list[dict] = []
        self.running = False
        self.started = False
        self.error = ""
        self._server: socket.socket | None = None
        self._discovery_socket: socket.socket | None = None
        self._clients: dict[int, socket.socket] = {}
        self._lock = threading.Lock()
        self._next_player_id = 2

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self._accept_loop, daemon=True)
        thread.start()
        discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        discovery_thread.start()

    def stop(self) -> None:
        self.running = False
        sockets = []
        if self._server is not None:
            sockets.append(self._server)
        if self._discovery_socket is not None:
            sockets.append(self._discovery_socket)
        with self._lock:
            sockets.extend(self._clients.values())
            self._clients.clear()
        for sock in sockets:
            try:
                sock.close()
            except OSError:
                pass

    def update_local_player(self, payload: dict) -> None:
        with self._lock:
            state = self.players.get(self.player_id) or RemotePlayerState(self.player_id)
            _apply_player_payload(state, payload)
            state.connected = True
            state.last_seen = time.time()
            self.players[self.player_id] = state

    def set_maze_state(self, maze_state: dict | None) -> None:
        with self._lock:
            self.maze_state = maze_state

    def drain_events(self) -> list[dict]:
        with self._lock:
            events = self.incoming_events[:]
            self.incoming_events.clear()
            return events

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "type": "state",
                "started": self.started,
                "preset": self.preset_key,
                "seed": self.maze_seed,
                "maze": self.maze_state,
                "players": [_player_to_payload(p) for p in self.players.values() if p.connected],
            }

    def _accept_loop(self) -> None:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            server.bind(("", MULTIPLAYER_PORT))
            server.listen(self.max_players - 1)
            server.settimeout(0.5)
            self._server = server
        except OSError as exc:
            self.error = f"HOST ERROR: {exc}"
            self.running = False
            return

        while self.running:
            try:
                client, _addr = self._server.accept()
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except socket.timeout:
                continue
            except OSError:
                break

            with self._lock:
                active_clients = [p for pid, p in self.players.items() if pid != self.player_id and p.connected]
                if len(active_clients) >= self.max_players - 1:
                    try:
                        _send_json(client, {"type": "reject", "message": "ROOM FULL"})
                        client.close()
                    except OSError:
                        pass
                    continue
                player_id = self._next_player_id
                self._next_player_id += 1
                self._clients[player_id] = client
                self.players[player_id] = RemotePlayerState(player_id, name=f"P{player_id}")

            thread = threading.Thread(target=self._client_loop, args=(client, player_id), daemon=True)
            thread.start()

    def _discovery_loop(self) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", DISCOVERY_PORT))
            sock.settimeout(0.35)
            self._discovery_socket = sock
        except OSError:
            return

        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            payload = _decode_discovery(data)
            if not payload or payload.get("type") != "discover":
                continue
            host_ip = _udp_reply_ip(addr[0])
            response = json.dumps({
                "magic": ROOM_DISCOVERY_MAGIC,
                "type": "offer",
                "host": host_ip,
                "tcp_port": MULTIPLAYER_PORT,
                "room_code": self.room_code,
                "codes": local_room_codes(),
            }, separators=(",", ":")).encode("utf-8")
            try:
                sock.sendto(response, addr)
            except OSError:
                continue

    def _client_loop(self, client: socket.socket, player_id: int) -> None:
        reader = JsonSocketReader(client)
        try:
            _send_json(client, {
                "type": "welcome",
                "player_id": player_id,
                "preset": self.preset_key,
                "seed": self.maze_seed,
                "max_players": self.max_players,
            })
            while self.running:
                message = reader.recv()
                if message is None:
                    break
                if message.get("type") == "player":
                    events = message.get("events", [])
                    with self._lock:
                        state = self.players.get(player_id) or RemotePlayerState(player_id)
                        _apply_player_payload(state, message)
                        state.connected = True
                        state.last_seen = time.time()
                        self.players[player_id] = state
                        if isinstance(events, list):
                            for event in events:
                                if isinstance(event, dict):
                                    self.incoming_events.append({"player_id": player_id, **event})
                    _send_json(client, self.snapshot())
        except (OSError, json.JSONDecodeError):
            pass
        finally:
            with self._lock:
                if player_id in self.players:
                    self.players[player_id].connected = False
                self._clients.pop(player_id, None)
            try:
                client.close()
            except OSError:
                pass


class MultiplayerClient:
    def __init__(self, host_code: str):
        self.host_code = normalize_room_code(host_code)
        self.player_id = 0
        self.preset_key = "classic"
        self.maze_seed = 0
        self.players: dict[int, RemotePlayerState] = {}
        self.maze_state: dict | None = None
        self.connected = False
        self.started = False
        self.error = ""
        self._socket: socket.socket | None = None
        self._reader: JsonSocketReader | None = None

    def connect(self, timeout: float = 4.0) -> bool:
        try:
            sock = socket.create_connection((self.host_code, MULTIPLAYER_PORT), timeout=timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(0.15)
            self._socket = sock
            self._reader = JsonSocketReader(sock)
            welcome = self._recv_wait(timeout)
            if not welcome:
                self.error = "NO RESPONSE FROM ROOM"
                self.close()
                return False
            if welcome.get("type") == "reject":
                self.error = welcome.get("message", "ROOM REJECTED")
                self.close()
                return False
            self.player_id = int(welcome["player_id"])
            self.preset_key = welcome.get("preset", "classic")
            self.maze_seed = int(welcome.get("seed", 0))
            self.connected = True
            sock.settimeout(0.002)
            return True
        except OSError as exc:
            self.error = format_join_error(exc, self.host_code)
            self.close()
            return False
        except (KeyError, ValueError, json.JSONDecodeError):
            self.error = "JOIN FAILED: ROOM SENT BAD DATA"
            self.close()
            return False

    def close(self) -> None:
        self.connected = False
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket = None
        self._reader = None

    def send_player(self, payload: dict) -> None:
        if not self.connected or self._socket is None:
            return
        try:
            _send_json(self._socket, {"type": "player", **payload})
        except OSError as exc:
            self.error = f"CONNECTION LOST: {exc}"
            self.close()

    def poll_state(self) -> None:
        if not self.connected or self._reader is None:
            return
        while self.connected:
            try:
                message = self._reader.recv()
            except socket.timeout:
                return
            except (OSError, json.JSONDecodeError) as exc:
                self.error = f"CONNECTION LOST: {exc}"
                self.close()
                return
            if message is None:
                self.error = "ROOM CLOSED"
                self.close()
                return
            if message.get("type") == "state":
                self.started = bool(message.get("started", False))
                self.preset_key = message.get("preset", self.preset_key)
                self.maze_seed = int(message.get("seed", self.maze_seed))
                self.maze_state = message.get("maze")
                self.players = {
                    int(p["id"]): _payload_to_player(p)
                    for p in message.get("players", [])
                    if "id" in p
                }

    def _recv_wait(self, timeout: float) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline and self._reader is not None:
            try:
                return self._reader.recv()
            except socket.timeout:
                continue
        return None


def _apply_player_payload(state: RemotePlayerState, payload: dict) -> None:
    state.name = str(payload.get("name", state.name or f"P{state.player_id}"))[:16]
    state.ship = int(payload.get("ship", state.ship))
    state.x = float(payload.get("x", state.x))
    state.y = float(payload.get("y", state.y))
    state.angle = float(payload.get("angle", state.angle))
    state.health = float(payload.get("health", state.health))
    state.max_health = float(payload.get("max_health", state.max_health))


def _player_to_payload(player: RemotePlayerState) -> dict:
    return {
        "id": player.player_id,
        "name": player.name,
        "ship": player.ship,
        "x": round(player.x, 2),
        "y": round(player.y, 2),
        "angle": round(player.angle, 2),
        "health": round(player.health, 1),
        "max_health": round(player.max_health, 1),
    }


def _payload_to_player(payload: dict) -> RemotePlayerState:
    state = RemotePlayerState(int(payload.get("id", 0)))
    _apply_player_payload(state, payload)
    return state
