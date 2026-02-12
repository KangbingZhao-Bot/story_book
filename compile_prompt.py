#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests


HARD_RULES = """【绝对不可删除/不可弱化的硬规则（必须保留含义）】
1) 画面里不出现任何人类（工人/路人/驾驶员/手脚/人影/倒影/海报人物都不出现）
2) 工程车无需驾驶员；禁止驾驶舱内景；车窗反光或深色不透明，看不到车内
3) 禁止车辆拟人化五官（眼睛/嘴巴/表情）
4) 车辆颜色固定（尤其翻翻：蓝色车头 + 黄色车斗；其他车按规则）
5) 输出必须覆盖全书页数（例如15页），按 1–N 逐页输出，不得省略/合并/总结；每页必须同时给：
   A. 本页文字（中文，句子短）
   B. 本页画面描述（中文，清晰可画）
6) 禁止输出“故事总结/概括”；最后一页必须是 N 页的内容
"""

SYSTEM_INSTRUCTIONS = """你是“绘本Prompt编译器”。你将把“全量Rules + 故事内容”压缩成一段用于 Gemini Storybook（一次生成整本书）的最终Prompt。
你必须严格遵守硬规则白名单，不能删除、弱化或引入矛盾。
你的输出要更短、更可执行，删除解释性/重复内容，保留和本故事相关的规则。
如果原规则里允许人物出现，视为与硬规则冲突，必须删除。
输出只包含【最终Prompt】正文，不要包含你的推理过程，不要额外解释。
"""

USER_TEMPLATE = """请把下面输入编译成一个“最终Prompt”（尽量短，目标 <= {max_chars} 中文字，但不得牺牲硬规则）。

{hard_rules}

【输入：全量Rules（可删减/压缩，但不能违反硬规则）】
--- rules/image_core.md ---
{image_core}

--- rules/style.md ---
{style}

--- rules/world.md ---
{world}

【输入：本书故事内容（必须逐页完整输出）】
--- story ---
{story}

【输出要求（必须满足）】
- 输出一个“最终Prompt”，适合直接粘贴到 Gemini Storybook，一次生成整本书。
- 必须要求模型按页编号 1..N 逐页输出，每页同时给“本页文字”和“本页画面描述”。
- 不得省略后半段；不得合并页；不得输出总结。
- 如果有结尾仪式，必须明确写在最后一页画面描述中。
"""


def read_text(p: Path) -> str:
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_text(encoding="utf-8", errors="replace").strip()


def call_chat_completions(
    api_base: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    url = api_base.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:2000]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"Unexpected response: {json.dumps(data, ensure_ascii=False)[:2000]}")


def main():
    ap = argparse.ArgumentParser(description="Compile/shorten rules+story into a final Storybook prompt via OpenAI-compatible API.")
    ap.add_argument("--story", required=True, help="Path to story markdown, e.g. stories/fanfan_today_decides.md")
    ap.add_argument("--rules-dir", default="rules", help="Rules directory (default: rules)")
    ap.add_argument("--out-dir", default="prompts", help="Output directory (default: prompts)")
    ap.add_argument("--max-chars", type=int, default=1400, help="Target max Chinese chars for final prompt (soft target)")
    ap.add_argument("--api-base", default=os.getenv("LLM_API_BASE", os.getenv("OPENAI_BASE_URL", "https://api.openai.com")),
                    help="API base URL, env: LLM_API_BASE or OPENAI_BASE_URL")
    ap.add_argument("--api-key", default=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
                    help="API key, env: LLM_API_KEY or OPENAI_API_KEY")
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
                    help="Model name, env: LLM_MODEL or OPENAI_MODEL")
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    if not args.api_key:
        print("Missing API key. Set LLM_API_KEY (or OPENAI_API_KEY) or pass --api-key", file=sys.stderr)
        sys.exit(2)

    root = Path.cwd()
    rules_dir = (root / args.rules_dir).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    story_path = (root / args.story).resolve()
    image_core = read_text(rules_dir / "image_core.md")
    style = read_text(rules_dir / "style.md")
    world = read_text(rules_dir / "world.md")
    story = read_text(story_path)

    user_prompt = USER_TEMPLATE.format(
        max_chars=args.max_chars,
        hard_rules=HARD_RULES,
        image_core=image_core,
        style=style,
        world=world,
        story=story,
    )

    compiled = call_chat_completions(
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model,
        system=SYSTEM_INSTRUCTIONS,
        user=user_prompt,
        temperature=args.temperature,
    ).strip()

    story_name = story_path.stem
    out_path = out_dir / f"{story_name}_optimized_prompt.md"
    out_path.write_text(compiled + "\n", encoding="utf-8")

    print(f"✅ Wrote: {out_path}")


if __name__ == "__main__":
    main()
