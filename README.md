# iny-material

**흩어진 자료를 전부 Markdown 으로 바꿔 재료 창고를 만드는 Claude Code 스킬입니다.**

이력서, 포트폴리오, 발표자료, 메모, 링크.
pdf·docx·hwp·이미지로 흩어져 있으면 AI 가 읽지 못합니다.
읽을 수 있는 하나의 형식으로 바꿔 한곳에 모읍니다.

에셋엔진 워크플로우의 **01단계**입니다.

---

## 이 스킬이 하는 일과 안 하는 일

| 합니다 | 안 합니다 |
|---|---|
| 형식 변환 | 고르기 |
| 출처·날짜 기록 | 분류·태그 |
| 목록 만들기 | 요약 |

**받은 걸 전부 넣습니다.** 무엇이 쓸모 있는지는 여기서 정하지 않습니다.

기준이 있어야 고를 수 있는데, 그 기준은 다음 단계에서 나옵니다.
여기서 미리 고르면 나중에 전부 다시 골라야 합니다.

그래서 이 단계는 빠릅니다. 판단할 게 없으니까요.

---

## 설치

```bash
git clone https://github.com/iny101400-young/iny-material.git
cd iny-material
bash install.sh ~/내작업폴더
```

경로를 안 주면 `~/asset-engine` 에 만듭니다.

설치되는 것은 두 가지입니다.

| | |
|---|---|
| 스킬 | `~/.claude/skills/iny-material/` |
| 작업 폴더 | 지정한 경로에 `raw/` `wiki/` `outputs/` 생성 |

---

## 쓰는 법

작업 폴더에서 Claude Code 를 열고 이렇게 칩니다.

```
재료화 시작
```

그러면 안내문이 나오고, **자료가 어디 있는지** 물어봅니다.
경로를 주면 형식별로 몇 개인지 세어 보여주고, 확인 질문 두어 개를 거쳐 전부 변환합니다.

---

## 나오는 것

```
raw/
  web/  pdfs/  images/  notes/  docs/
.kb/manifest.json
```

파일마다 머리에 이게 붙습니다.

```yaml
---
source: 원본 URL 또는 파일 경로
ingested_at: 2026-08-25T13:00:00Z
type: web | pdf | image | note | doc
status: uncompiled
---
```

`status: uncompiled` 는 **아직 안 쓴 재료**라는 표시입니다.
다음 단계가 이걸 보고 새로 들어온 것만 처리합니다. 자료가 늘어나도 처음부터 다시 돌리지 않습니다.

---

## 알아둘 것

**원본은 건드리지 않습니다.** 읽고 복사만 합니다. 지우거나 옮기지 않습니다.

**한글 파일(.hwp)은 변환 도구가 필요합니다.** 없으면 조용히 넘기지 않고 어떤 파일이 남았는지 알려줍니다.
`pip install pyhwp` 한 줄이면 되고, 한글에서 PDF 로 저장하셔도 됩니다.

**옵시디언 볼트가 자료 안에 있으면** 통째로 넣을지, 빼고 갈지, 건너뛸지 물어봅니다.

**이미 다른 사이트에 올려둔 자료가 있으면** 알려드립니다.
같은 글이 두 곳에 있으면 나중에 어느 쪽이 효과 있었는지 비교할 수 없게 되기 때문입니다.

---

## 필요한 것

| | |
|---|---|
| [Claude Code](https://claude.com/claude-code) | 스킬은 여기서 돌아갑니다 |
| macOS | `textutil` 로 doc·docx·rtf 를 읽습니다 |
| `pdftotext` | PDF 용. 없으면 Claude 가 직접 읽습니다 |
| `pyhwp` | 한글 파일이 있을 때만 (선택) |

---

## 다음 단계

01 이 끝나면 스킬이 다음 링크를 알려줍니다.
단계마다 스킬 하나씩, 끝나면 다음을 알려주는 구조입니다. **한 번에 하나만 아시면 됩니다.**

```
01 material  →  02 identify  →  03 structure  →  04 design
→  05 tech  →  06 build  →  07 admin  →  08 measure  ⟳
```

---

## 출처

이 스킬은 [louiswang524/llm-knowledge-base](https://github.com/louiswang524/llm-knowledge-base)
의 `kb-ingest` (MIT, Copyright (c) 2026 Louis Wang) 를 바탕으로 고쳤습니다.

바꾼 곳은 이렇습니다.

| 원본 | 이 스킬 |
|---|---|
| 한 번에 하나씩 | 폴더째 전량 |
| 바로 변환 | 먼저 형식별 개수를 세어 보여줌 |
| web·pdf·image·note | doc·docx·rtf·hwp 추가 |
| Obsidian 볼트 전제 | 볼트가 있으면 물어봄 |
| | 이미 다른 곳에 올린 자료인지 물어봄 |

라이선스는 [MIT](LICENSE) 입니다.
