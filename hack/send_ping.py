"""Ping イベント送信スクリプト。

HTTP POST で /api/v1/events に Ping イベントを送信する開発・テスト用スクリプト。
"""

import argparse
import http.client
import json
import sys
import time


def create_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成する。"""
    parser = argparse.ArgumentParser(
        description="Ping イベントをサーバーに送信する",
    )
    parser.add_argument(
        "-H",
        "--host",
        default="localhost",
        help="サーバーホスト (デフォルト: localhost)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="サーバーポート (デフォルト: 8080)",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        default=0,
        help="遅延秒数 (デフォルト: 0)",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=1,
        help="送信回数 (デフォルト: 1)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=0.0,
        help="送信間隔（秒） (デフォルト: 0.0)",
    )
    return parser


def send_ping(host: str, port: int, delay: int) -> tuple[bool, str]:
    """Ping イベントを送信する。

    Args:
        host: サーバーホスト
        port: サーバーポート
        delay: 遅延秒数

    Returns:
        (成功フラグ, メッセージ) のタプル
    """
    payload = {"type": "ping", "payload": {}, "delay": delay}

    try:
        conn = http.client.HTTPConnection(host, port, timeout=30)
        try:
            conn.request(
                "POST",
                "/api/v1/events",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
            body = response.read().decode("utf-8")

            if response.status == 200 or response.status == 201:
                try:
                    data = json.loads(body)
                    event_id = data.get("event_id", "unknown")
                    return True, event_id
                except json.JSONDecodeError:
                    return False, f"Invalid JSON response: {body}"
            else:
                return False, f"{response.status} {response.reason}"
        finally:
            conn.close()
    except ConnectionRefusedError:
        return False, "Connection refused"
    except TimeoutError:
        return False, "Connection timeout"
    except OSError as e:
        return False, str(e)


def main() -> int:
    """メインエントリーポイント。"""
    parser = create_parser()
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/api/v1/events"
    print(f"Sending ping to {url}...")

    for i in range(args.count):
        if i > 0 and args.interval > 0:
            time.sleep(args.interval)

        success, message = send_ping(args.host, args.port, args.delay)

        if success:
            print(f"[{i + 1}/{args.count}] Event ID: {message} (delay: {args.delay}s)")
        else:
            print(f"Error: {message}")
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
