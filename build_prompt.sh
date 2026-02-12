#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

story_file="${1:-}"
if [[ -z "$story_file" ]]; then
  echo "Usage: ./build_prompt.sh stories/xxx.md"
  exit 1
fi

if [[ ! -f "$story_file" ]]; then
  echo "Story file not found: $story_file"
  exit 1
fi

story_name="$(basename "$story_file" .md)"
output="${ROOT_DIR}/prompts/${story_name}_prompt.md"
template="${ROOT_DIR}/builder/prompt_template.md"

mkdir -p "${ROOT_DIR}/prompts"

tmp="$(mktemp)"

sed \
  -e "/\[IMAGE_CORE\]/r ${ROOT_DIR}/rules/image_core.md" -e "s/\[IMAGE_CORE\]//" \
  -e "/\[WORLD\]/r ${ROOT_DIR}/rules/world.md" -e "s/\[WORLD\]//" \
  -e "/\[STYLE\]/r ${ROOT_DIR}/rules/style.md" -e "s/\[STYLE\]//" \
  -e "/\[STORY\]/r ${story_file}" -e "s/\[STORY\]//" \
  "${template}" > "${tmp}"

repo_commit="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
rules_commit="$(git log -n 1 --pretty=format:%h -- rules 2>/dev/null || echo "${repo_commit}")"
build_time="$(date '+%Y-%m-%d %H:%M:%S %z')"

cat > "${output}" <<HEADER
<!--
Generated: ${build_time}
Repo commit: ${repo_commit}
Rules commit: ${rules_commit}
Story file: ${story_file}
-->
HEADER

cat "${tmp}" >> "${output}"
rm -f "${tmp}"

echo "✅ Prompt generated -> ${output}"
