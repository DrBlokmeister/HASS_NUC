"""Helpers for discovering secondary AP hubs from AP payloads."""

from __future__ import annotations

import ipaddress
from typing import Any


def normalize_ip(value: Any) -> str | None:
    """Return normalized IP if value is a valid IP string."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    try:
        return str(ipaddress.ip_address(cleaned))
    except ValueError:
        return None


def extract_remote_hub_evidence(payload: Any, main_hub_ip: str | None) -> list[dict[str, Any]]:
    """Extract possible remote AP hub evidence from a nested payload."""
    discovered: list[dict[str, Any]] = []
    seen_ips: set[str] = set()

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            key_lower_map = {str(k).lower(): k for k in node.keys()}
            for ip_key in ("ip", "ap_ip", "hub_ip", "remote_ip", "remoteip"):
                if ip_key in key_lower_map:
                    raw = node.get(key_lower_map[ip_key])
                    ip = normalize_ip(raw)
                    if ip and ip != main_hub_ip and ip not in seen_ips:
                        discovered.append({
                            "hub_id": ip,
                            "ip": ip,
                            "metadata": dict(node),
                            "evidence_path": path or "$",
                        })
                        seen_ips.add(ip)

            for key, value in node.items():
                key_l = str(key).lower()
                child_path = f"{path}.{key}" if path else str(key)
                if isinstance(value, str):
                    ip_value = normalize_ip(value)
                    if (
                        ip_value
                        and ip_value != main_hub_ip
                        and ip_value not in seen_ips
                        and any(token in key_l for token in ("hub", "ap", "remote", "ip"))
                    ):
                        discovered.append({
                            "hub_id": ip_value,
                            "ip": ip_value,
                            "metadata": {"field": key, "value": value},
                            "evidence_path": child_path,
                        })
                        seen_ips.add(ip_value)
                walk(value, child_path)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, f"{path}[{idx}]")

    walk(payload)
    return discovered


def resolve_connected_ap(
    apip: Any,
    main_hub_ip: str | None,
    fallback_host: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve tag connected AP from explicit apip field."""
    normalized = normalize_ip(apip)
    if isinstance(apip, str) and apip.strip() == "0.0.0.0":
        return main_hub_ip or fallback_host, "tag.apip_zero_fallback_main_hub"
    if normalized is None:
        return None, None
    return normalized, "tag.apip"
