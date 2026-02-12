#!/bin/bash

story_file=$1
story_name=$(basename "$story_file" .md)

output="../prompts/${story_name}_prompt.md"

sed \
  -e "/\[IMAGE_CORE\]/r ../rules/image_core.md" -e "s/\[IMAGE_CORE\]//" \
  -e "/\[WORLD\]/r ../rules/world.md" -e "s/\[WORLD\]//" \
  -e "/\[STYLE\]/r ../rules/style.md" -e "s/\[STYLE\]//" \
  -e "/\[STORY\]/r $story_file" -e "s/\[STORY\]//" \
  prompt_template.md > "$output"

echo "✅ Prompt generated -> $output"
