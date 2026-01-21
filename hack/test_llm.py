"""LLM テスト用スクリプト。

strands-agents + LiteLLM/Ollama を使用して設定ファイルの LLM 設定をテストする。
"""

import argparse
import sys
from pathlib import Path

import litellm
from strands import Agent

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from myao3.config.loader import load_config
from myao3.config.models import LLMConfig
from myao3.infrastructure.llm.litellm_model import Model, create_model


def create_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成する。"""
    parser = argparse.ArgumentParser(
        description="LLM 設定をテストする",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="設定ファイルのパス (デフォルト: config.yaml)",
    )
    parser.add_argument(
        "-m",
        "--message",
        default="こんにちは。自己紹介をしてください。",
        help="送信するメッセージ (デフォルト: 'こんにちは。自己紹介をしてください。')",
    )
    parser.add_argument(
        "-s",
        "--system-prompt",
        help="システムプロンプト (デフォルト: 設定ファイルの agent.system_prompt)",
    )
    parser.add_argument(
        "--no-system-prompt",
        action="store_true",
        help="システムプロンプトを使用しない",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="詳細な出力を表示",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="LiteLLM を直接呼び出す（strands-agents を経由しない）",
    )
    return parser


def main() -> int:
    """メインエントリーポイント。"""
    parser = create_parser()
    args = parser.parse_args()

    # 設定ファイル読み込み
    print(f"Loading config from: {args.config}")
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1

    llm_config = config.agent.llm

    if args.verbose:
        print(f"Model ID: {llm_config.model_id}")
        print(f"Params: {llm_config.params}")
        # api_key は隠す
        safe_client_args = {
            k: ("***" if "key" in k.lower() else v)
            for k, v in llm_config.client_args.items()
        }
        print(f"Client args: {safe_client_args}")
        print()

    # Model 作成
    print(f"Creating model with model_id: {llm_config.model_id}")
    try:
        model = create_model(llm_config)
        print(f"Model type: {type(model).__name__}")
    except Exception as e:
        print(f"Error creating model: {e}")
        return 1

    # システムプロンプト決定
    if args.no_system_prompt:
        system_prompt = None
    elif args.system_prompt:
        system_prompt = args.system_prompt
    else:
        system_prompt = config.agent.system_prompt

    if args.verbose and system_prompt:
        print(f"System prompt (first 100 chars): {system_prompt[:100]}...")
        print()

    # クエリ実行
    print(f"Sending message: {args.message}")
    print("-" * 40)

    if args.raw:
        # LiteLLM を直接呼び出す
        return _run_raw_litellm(llm_config, system_prompt, args.message, args.verbose)
    else:
        # strands-agents を経由して呼び出す
        return _run_with_strands(model, system_prompt, args.message, args.verbose)


def _run_raw_litellm(
    llm_config: LLMConfig,
    system_prompt: str | None,
    message: str,
    verbose: bool,
) -> int:
    """LiteLLM を直接呼び出す。"""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})

    try:
        if verbose:
            print(f"Calling litellm.completion with {len(messages)} messages...")

        response = litellm.completion(
            model=llm_config.model_id,
            messages=messages,
            **llm_config.params,
            **llm_config.client_args,
        )

        if verbose:
            print(f"Response type: {type(response)}")
            print(f"Response: {response}")
            print()

        content = response.choices[0].message.content
        print(content)
    except Exception as e:
        print(f"Error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    print("-" * 40)
    print("Done.")
    return 0


def _run_with_strands(
    model: Model,
    system_prompt: str | None,
    message: str,
    verbose: bool,
) -> int:
    """strands-agents を経由して呼び出す。"""
    print("Creating Agent...")
    try:
        agent = Agent(model=model, system_prompt=system_prompt)
    except Exception as e:
        print(f"Error creating agent: {e}")
        return 1

    try:
        result = agent(message)
        if verbose:
            print(f"Result type: {type(result)}")
            print(f"Result repr: {repr(result)}")
            if hasattr(result, "__dict__"):
                print(f"Result attrs: {result.__dict__}")
            if hasattr(result, "message"):
                print(f"Result message: {result.message}")
            if hasattr(result, "stop_reason"):
                print(f"Result stop_reason: {result.stop_reason}")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    print("-" * 40)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
