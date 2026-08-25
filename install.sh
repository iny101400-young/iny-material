#!/usr/bin/env bash
# iny-material 설치
# 사용법:  bash install.sh [작업폴더경로]
#          경로를 안 주면 ~/asset-engine 에 만듭니다.
set -e
KB_PATH="${1:-$HOME/asset-engine}"
KB_PATH="${KB_PATH/#\~/$HOME}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$KB_PATH"/raw/{web,pdfs,images,notes,docs}
mkdir -p "$KB_PATH"/wiki/{concepts,sources,archive}
mkdir -p "$KB_PATH"/outputs "$KB_PATH"/.kb
[ -f "$KB_PATH/.kb/manifest.json" ] || echo '{}' > "$KB_PATH/.kb/manifest.json"
[ -f "$KB_PATH/wiki/index.md" ] || printf '# 위키 목차\n\n03 단계에서 채워집니다.\n\n## Concepts\n\n## Sources\n' > "$KB_PATH/wiki/index.md"
[ -d "$KB_PATH/.git" ] || git -C "$KB_PATH" init -q

DEST="$HOME/.claude/skills/iny-material"
mkdir -p "$DEST"
cp "$SRC/SKILL.md" "$DEST/SKILL.md"
rm -rf "$DEST/scripts"
cp -R "$SRC/scripts" "$DEST/scripts"      # 한글·pptx·xlsx 폴백. 없으면 hwp 를 못 뽑습니다

mkdir -p "$HOME/.claude"
cat > "$HOME/.claude/iny-config.json" <<CFG
{
  "kb_path": "$KB_PATH"
}
CFG

echo
echo "설치됐습니다."
echo "  스킬      ~/.claude/skills/iny-material/"
echo "  작업 폴더  $KB_PATH"
echo
echo "Claude Code 를 $KB_PATH 에서 열고 '재료화 시작' 이라고 치세요."
