#!/usr/bin/env python3
"""
Somnia register eligibility checker.

Input:
  - addresses.txt: one public EVM address per line
  - proxies.txt: optional, one proxy per line

No private keys, mnemonics, signatures, or wallet connections are used.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_URL = "https://register.somnia.network/api/eligibility"
APP_ID = "somnia_p2"
DEFAULT_ADDRESSES = Path("addresses.txt")
DEFAULT_PROXIES = Path("proxies.txt")
DEFAULT_OUTPUT = Path("somnia_register_results.txt")
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


@dataclass
class CheckResult:
    address: str
    eligible: bool
    allocation: float
    status: str
    error: str = ""


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    values: list[str] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            values.append(value)
    return values


def read_addresses(path: Path) -> list[str]:
    addresses = []
    for value in read_lines(path):
        address = value.split()[0].split(",")[0].strip()
        if ADDRESS_RE.match(address):
            addresses.append(address)
        else:
            print(f"Skip invalid address: {value}")

    if not addresses:
        raise ValueError(f"No valid addresses found in {path}")

    return addresses


def normalize_proxy(proxy: str) -> str:
    proxy = proxy.strip()
    if not proxy:
        return proxy

    if "://" not in proxy:
        proxy = f"http://{proxy}"

    return proxy


def build_opener(proxy: str | None) -> urllib.request.OpenerDirector:
    if not proxy:
        return urllib.request.build_opener()

    normalized_proxy = normalize_proxy(proxy)
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(
            {
                "http": normalized_proxy,
                "https": normalized_proxy,
            }
        )
    )


def post_json(
    url: str,
    payload: dict[str, Any],
    timeout: int,
    proxy: str | None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "clq-app-id": APP_ID,
            "origin": "https://register.somnia.network",
            "referer": "https://register.somnia.network/flow",
            "user-agent": "Mozilla/5.0",
        },
    )

    opener = build_opener(proxy)

    try:
        with opener.open(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text or "{}")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"error": text}
        return error.code, data


def get_proxy_for_index(proxies: list[str], index: int) -> str | None:
    if not proxies:
        return None

    return proxies[index % len(proxies)]


def check_address(address: str, timeout: int, proxy: str | None) -> CheckResult:
    status_code, data = post_json(API_URL, {"evmAddresses": [address]}, timeout, proxy)

    if status_code != 200:
        return CheckResult(
            address=address,
            eligible=False,
            allocation=0,
            status=f"HTTP {status_code}",
            error=json.dumps(data, ensure_ascii=False),
        )

    total = data.get("total")
    if total is None:
        return CheckResult(
            address=address,
            eligible=False,
            allocation=0,
            status="error",
            error=f"Unexpected response: {json.dumps(data, ensure_ascii=False)}",
        )

    try:
        allocation = float(total)
    except ValueError:
        return CheckResult(
            address=address,
            eligible=False,
            allocation=0,
            status="error",
            error=f"Invalid allocation value: {total}",
        )

    eligible = bool(data.get("eligible")) or allocation > 0
    return CheckResult(
        address=address,
        eligible=eligible,
        allocation=allocation,
        status="Eligible" if eligible else "Not eligible",
    )


def format_allocation(value: float) -> str:
    if value.is_integer():
        return str(int(value))

    return f"{value:.8f}".rstrip("0").rstrip(".")


def result_to_line(result: CheckResult) -> str:
    eligible_text = "eligible" if result.eligible else "not eligible"
    allocation_text = format_allocation(result.allocation)
    line = f"{result.address} - {eligible_text} - allocation: {allocation_text}"
    if result.error:
        line += f" - error: {result.error}"
    return line


def write_results(output_path: Path, results: list[CheckResult]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(result_to_line(result) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Somnia register eligibility by public addresses only.")
    parser.add_argument("--addresses", type=Path, default=DEFAULT_ADDRESSES, help="TXT file with addresses")
    parser.add_argument("--proxies", type=Path, default=DEFAULT_PROXIES, help="Optional TXT file with proxies")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output TXT file")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests in seconds")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    addresses = read_addresses(args.addresses)
    proxies = read_lines(args.proxies)

    print(f"Loaded addresses: {len(addresses)}")
    print(f"Loaded proxies: {len(proxies)}")

    results: list[CheckResult] = []

    for index, address in enumerate(addresses):
        proxy = get_proxy_for_index(proxies, index)

        try:
            result = check_address(address, args.timeout, proxy)
        except Exception as error:
            result = CheckResult(
                address=address,
                eligible=False,
                allocation=0,
                status="error",
                error=str(error),
            )

        results.append(result)

        proxy_text = f" | proxy #{index % len(proxies) + 1}" if proxies else ""
        print(
            f"[{index + 1}/{len(addresses)}] {result_to_line(result)}"
            f"{proxy_text}"
        )

        if index + 1 < len(addresses) and args.delay > 0:
            time.sleep(args.delay)

    eligible_results = [result for result in results if result.eligible]
    total_allocation = sum(result.allocation for result in eligible_results)

    print("")
    print(f"Checked wallets: {len(results)}")
    print(f"Eligible wallets: {len(eligible_results)}")
    print(f"Total allocation: {format_allocation(total_allocation)} SOMI")

    write_results(args.output, results)
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
