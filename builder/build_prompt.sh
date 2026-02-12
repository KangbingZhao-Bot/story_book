#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

story_file="${1:-}"
if [[ -z "$story_file" ]]; then
  echo "Usage: $0 <story_file.md>"
  exit 1
fi

# Allow passing relative paths from anywhere
if [[ ! -f "$story_file" ]]; then
  if [[ -f "${ROOT_DIR}/${story_file}" ]]; then
    story_file="${ROOT_DIR}/${story_file}"
  else
    echo "Story file not found: $story_file"
    exit 1
  fi
fi

story_name="$(basename "$story_file" .md)"
output="${ROOT_DIR}/prompts/${story_name}_prompt.md"
template="${SCRIPT_DIR}/prompt_template.md"

mkdir -p "${ROOT_DIR}/prompts"

# Build the body first
tmp="$(mktemp)"
sed \
  -e "/\[IMAGE_CORE\]/r ${ROOT_DIR}/rules/image_core.md" -e "s/\[IMAGE_CORE\]//" \
  -e "/\[WORLD\]/r ${ROOT_DIR}/rules/world.md" -e "s/\[WORLD\]//" \
  -e "/\[STYLE\]/r ${ROOT_DIR}/rules/style.md" -e "s/\[STYLE\]//" \
  -e "/\[STORY\]/r ${story_file}" -e "s/\[STORY\]//" \
  "${template}" > "${tmp}"

# Repro header
repo_commit="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
rules_commit="$(git -C "${ROOT_DIR}" log -n 1 --pretty=format:%h -- rules 2>/dev/null || echo "${repo_commit}")"
story_rel="${story_file#${ROOT_DIR}/}"
build_time="$(date '+%Y-%m-%d %H:%M:%S %z')"

cat > "${output}" <<HEADER
<!--
Generated: ${build_time}
Repo commit: ${repo_commit}
Rules commit: ${rules_commit}
Story file: ${story_rel}
-->
HEADER

cat "${tmp}" >> "${output}"
rm -f "${tmp}"

echo "✅ Prompt generated -> ${output}"
