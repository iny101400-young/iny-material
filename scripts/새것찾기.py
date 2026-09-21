#!/usr/bin/env python3
"""
지난번 뒤에 새로 생긴 것만 골라낸다. 설치 없이, 파이썬 표준 라이브러리만 쓴다.

    python3 새것찾기.py {KB_PATH} {자료경로} [{자료경로} ...]

★ 왜 필요한가.

재료화를 두 번째 돌릴 때 전부 다시 훑으면 두 가지가 망가진다.

  하나  이미 담은 수천 개를 또 변환한다. 시간도 시간이지만 같은 재료가 두 벌이 된다
  둘    사람이 판단해 뺐던 것을 또 만난다. 같은 질문에 또 답해야 한다

그래서 목록(manifest)에 이미 있는 것과 제외 목록에 적힌 것을 빼고,
**남은 것만** 내놓는다. 남은 게 0 개면 0 개라고 말한다 — 그것도 답이다.

★ 무엇으로 「같다」를 판단하나.

원본 경로로 본다. 목록의 `source` 값과 맞춰 본다.
파일 내용이 바뀐 경우는 경로가 같으니 「새것」이 아니라 **「바뀐 것」**으로 따로 낸다.
바뀐 것은 담을지 말지를 사람이 정해야 한다 — 덮어쓰면 앞 판이 사라지기 때문이다.

이름이 바뀐 파일은 새것으로 잡힌다. 그건 이 방법의 한계이고, 숨기지 않고 적어 둔다.
내용 해시로 보면 잡히지만, 수천 개를 매번 해시하면 느려서 안 한다.

내는 것
    새것     목록에 없는 파일
    바뀐것   목록에 있는데 원본이 더 나중에 고쳐진 파일
    그대로   목록에 있고 안 바뀐 파일 (개수만)
    뺀것     제외 목록 규칙에 걸린 파일 (개수만)
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

# 이름만 보고 자르는 것. SKILL.md 3-1 표와 같아야 한다.
# 여기만 고치고 표를 안 고치면 화면 설명과 실제가 어긋난다.
자를폴더 = {
    'node_modules', 'site-packages', 'vendor', '.venv', 'bower_components', 'Pods',
    '.git', '__pycache__', '.next', '.nuxt', '.vercel', '.gradle', '_site', 'build',
}
자를끝 = ('.pyc', '.so', '.dylib', '.lock')
자를이름 = {'.DS_Store', 'Thumbs.db'}


def 고르기(s):
    """맥에서 한글 파일명은 자모가 갈라져 온다(NFD). 맞춰 보려면 NFC 로 모은다."""
    return unicodedata.normalize('NFC', s)


def 펴기(길):
    """
    경로를 하나의 꼴로 편다.

    ★ 안 펴면 같은 파일을 두 번 담는다.
    목록에는 절대경로로 적혀 있는데 훑을 때 상대경로로 들어오면 글자가 달라서
    「목록에 없다」가 된다. 실제로 이미 담은 파일이 새것으로 잡혔다.
    바로가기도 여기서 같이 푼다(realpath).
    """
    return 고르기(os.path.realpath(os.path.expanduser(str(길))))


def 훑기(뿌리):
    """자료 폴더를 훑어 파일 경로를 낸다. 바로가기(-L)도 따라간다."""
    나온것 = []
    for 곳, 폴더들, 파일들 in os.walk(뿌리, followlinks=True):
        폴더들[:] = [d for d in 폴더들 if d not in 자를폴더 and not d.endswith('.dist-info')]
        for f in 파일들:
            if f in 자를이름 or f.endswith(자를끝):
                continue
            나온것.append(os.path.join(곳, f))
    return 나온것


def 목록읽기(kb):
    """{원본경로NFC: 담은때(epoch)} 를 만든다. 없으면 빈 것을 준다."""
    길 = os.path.join(kb, '.kb', 'manifest.json')
    try:
        with open(길, encoding='utf-8') as fp:
            판 = json.load(fp)
    except (OSError, ValueError):
        return {}, False
    # 목록은 {파일이름: {...}} 꼴이다. source 가 원본 경로다
    담긴것 = {}
    for 값 in (판.values() if isinstance(판, dict) else []):
        if not isinstance(값, dict):
            continue
        원본 = 값.get('source')
        if not 원본:
            continue
        때 = 0.0
        적힌때 = 값.get('ingested_at')
        if 적힌때:
            try:
                때 = datetime.fromisoformat(str(적힌때).replace('Z', '+00:00')).timestamp()
            except ValueError:
                때 = 0.0
        담긴것[펴기(원본)] = 때
    return 담긴것, True


def 제외읽기(kb):
    """제외목록.md 의 표에서 규칙만 읽는다. 사람이 읽는 설명은 무시한다."""
    길 = os.path.join(kb, '제외목록.md')
    뺄것, 살릴것 = [], []
    try:
        with open(길, encoding='utf-8') as fp:
            글 = fp.read()
    except OSError:
        return 뺄것, 살릴것
    for 줄 in 글.splitlines():
        칸 = [c.strip() for c in 줄.split('|')]
        if len(칸) < 3:
            continue
        무엇 = 칸[1]
        길찾기 = re.search(r'`([^`]+)`', 칸[2])
        if not 길찾기:
            continue
        경로 = 고르기(길찾기.group(1))
        if 무엇 == '빼기':
            뺄것.append(경로)
        elif 무엇 == '넣기':
            살릴것.append(경로)
    return 뺄것, 살릴것


def 걸리나(경로, 규칙들):
    """규칙은 경로 조각이다. 그 조각이 경로 안에 있으면 걸린 것으로 본다."""
    return any(r in 경로 for r in 규칙들)


def 돌리기(kb, 자료길들):
    담긴것, 목록있나 = 목록읽기(kb)
    뺄것, 살릴것 = 제외읽기(kb)

    새것, 바뀐것 = [], []
    그대로 = 뺀것 = 0

    for 뿌리 in 자료길들:
        for 길 in 훑기(뿌리):
            키 = 펴기(길)
            if 걸리나(키, 뺄것) and not 걸리나(키, 살릴것):
                뺀것 += 1
                continue
            담은때 = 담긴것.get(키)
            if 담은때 is None:
                새것.append(길)
                continue
            try:
                고친때 = os.path.getmtime(길)
            except OSError:
                고친때 = 0.0
            # 담은 뒤에 고쳐졌으면 「바뀐 것」이다. 1분은 저장 시각 오차를 봐준 것이다
            if 담은때 and 고친때 > 담은때 + 60:
                바뀐것.append(길)
            else:
                그대로 += 1

    새것.sort()
    바뀐것.sort()
    return {
        '목록있나': 목록있나,
        '새것': 새것,
        '바뀐것': 바뀐것,
        '그대로': 그대로,
        '뺀것': 뺀것,
        '잰때': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
    }


def 보이기(판):
    if not 판['목록있나']:
        print('목록이 없습니다. 처음 담는 것이라 전부가 새것입니다.\n')
    print(f"새것 {len(판['새것'])}개 · 바뀐 것 {len(판['바뀐것'])}개 "
          f"· 그대로 {판['그대로']}개 · 규칙으로 뺀 것 {판['뺀것']}개\n")

    if not 판['새것'] and not 판['바뀐것']:
        print('지난번 뒤에 새로 생긴 것이 없습니다. 담을 것이 없다는 뜻입니다.')
        return

    if 판['새것']:
        print('=== 새것 · 목록에 없던 파일 ===')
        칸 = {}
        for 길 in 판['새것']:
            끝 = 길.rsplit('.', 1)[-1].lower() if '.' in os.path.basename(길) else '(없음)'
            칸.setdefault(끝, []).append(길)
        for 끝, 것들 in sorted(칸.items(), key=lambda x: -len(x[1])):
            print(f'  {끝:>6}  {len(것들):>4}개')
        print()
        for 길 in 판['새것'][:40]:
            print('   ', 길)
        if len(판['새것']) > 40:
            print(f"    … 그리고 {len(판['새것']) - 40}개 더")
        print()

    if 판['바뀐것']:
        print('=== 바뀐 것 · 담은 뒤에 원본이 고쳐진 파일 ===')
        print('담으면 앞 판이 사라집니다. 담을지는 사람이 정합니다.')
        for 길 in 판['바뀐것'][:20]:
            print('   ', 길)
        if len(판['바뀐것']) > 20:
            print(f"    … 그리고 {len(판['바뀐것']) - 20}개 더")


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip())
        sys.exit(2)
    인자 = sys.argv[1:]
    # 깃발을 먼저 뗀다. 안 떼면 `--json` 을 자료 폴더로 알고 훑으려 든다
    json으로 = '--json' in 인자
    인자 = [a for a in 인자 if a != '--json']
    if len(인자) < 2:
        print(__doc__.strip())
        sys.exit(2)
    kb, 자료길들 = 인자[0], 인자[1:]
    판 = 돌리기(kb, 자료길들)
    print(json.dumps(판, ensure_ascii=False, indent=2) if json으로 else '', end='')
    if not json으로:
        보이기(판)


if __name__ == '__main__':
    main()
