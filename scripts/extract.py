#!/usr/bin/env python3
"""
설치 없이 글자를 뽑는다. 파이썬 표준 라이브러리만 쓴다.

    python3 extract.py "파일.hwp"

  hwp    OLE(CFB) 컨테이너를 직접 파싱해 문단 텍스트를 뽑는다 (HWP 5.x, 비암호화)
  hwpx   ZIP + XML
  pptx   ZIP + XML (슬라이드 순서대로)
  xlsx   ZIP + XML (시트·행 단위)

첫 줄에 `# 형식:` 과 `# 서식소실:` 을 찍는다. 서식소실이 yes 면
재료 md 머리말에 `layout_lost:` 를 남겨야 한다.

한계는 README 가 아니라 여기 적어 둔다.
  안 되는 것   HWP 3.x 이하 · 암호화된 문서 · 이미지 · 도형 · 각주 · 머리말/꼬리말
  잃는 것      표의 행·열 관계. 셀 글자는 나오지만 표 모양은 복원되지 않는다
"""
import io
import re
import struct
import sys
import zipfile
import zlib

# ────────────────────────────────────────────────────────── HWP 5.x (OLE/CFB)

CFB_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def read_cfb(data):
    """CFB 컨테이너에서 {스트림이름: bytes} 를 복원한다."""
    if data[:8] != CFB_MAGIC:
        raise ValueError('CFB 아님')
    ssz = 1 << struct.unpack_from('<H', data, 0x1e)[0]      # 섹터 크기
    mss = 1 << struct.unpack_from('<H', data, 0x20)[0]      # 미니 섹터 크기
    n_fat = struct.unpack_from('<I', data, 0x2c)[0]
    dir_st = struct.unpack_from('<I', data, 0x30)[0]
    mini_c = struct.unpack_from('<I', data, 0x3c)[0]        # 미니 FAT 시작
    difat_st, n_difat = struct.unpack_from('<II', data, 0x44)

    def sec(i):
        return data[(i + 1) * ssz:(i + 2) * ssz]

    # DIFAT 를 따라가 FAT 섹터 목록을 모은다
    fat_secs = [x for x in struct.unpack_from('<109I', data, 0x4c) if x != 0xFFFFFFFF]
    nxt = difat_st
    for _ in range(n_difat):
        if nxt >= 0xFFFFFFFE:
            break
        ent = struct.unpack('<%dI' % (ssz // 4), sec(nxt))
        fat_secs += [x for x in ent[:-1] if x != 0xFFFFFFFF]
        nxt = ent[-1]
    fat = []
    for s in fat_secs[:n_fat if n_fat else len(fat_secs)]:
        fat += list(struct.unpack('<%dI' % (ssz // 4), sec(s)))

    def chain(start):
        out, c, guard = [], start, 0
        while c < 0xFFFFFFFE and guard < 1 << 20:
            out.append(c)
            c = fat[c] if c < len(fat) else 0xFFFFFFFE
            guard += 1
        return out

    dirdata = b''.join(sec(i) for i in chain(dir_st))
    entries = []
    for i in range(0, len(dirdata), 128):
        e = dirdata[i:i + 128]
        if len(e) < 128:
            break
        nlen = struct.unpack_from('<H', e, 0x40)[0]
        name = e[:max(0, nlen - 2)].decode('utf-16-le', 'replace')
        entries.append((name, e[0x42],
                        struct.unpack_from('<I', e, 0x74)[0],
                        struct.unpack_from('<Q', e, 0x78)[0]))

    minifat = []
    if mini_c < 0xFFFFFFFE:
        md = b''.join(sec(i) for i in chain(mini_c))
        minifat = list(struct.unpack('<%dI' % (len(md) // 4), md))
    root = entries[0]
    minidata = b''.join(sec(i) for i in chain(root[2])) if root[3] else b''
    cut = struct.unpack_from('<I', data, 0x38)[0]           # 미니 스트림 기준 크기

    def stream(start, size, mini):
        if mini:
            out, c, guard = b'', start, 0
            while c < 0xFFFFFFFE and guard < 1 << 20:
                out += minidata[c * mss:(c + 1) * mss]
                c = minifat[c] if c < len(minifat) else 0xFFFFFFFE
                guard += 1
            return out[:size]
        return b''.join(sec(i) for i in chain(start))[:size]

    return {name: stream(start, size, size < cut)
            for name, typ, start, size in entries if typ == 2 and size}


# 확장 컨트롤은 16바이트, 인라인 컨트롤은 2바이트를 차지한다
CTRL_EXTENDED = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
CTRL_INLINE = {4, 5, 6, 7, 8, 19, 20}
HWPTAG_PARA_TEXT = 67


def hwp_paragraphs(body):
    """레코드를 훑어 문단 텍스트만 모은다."""
    out, p, n = [], 0, len(body)
    while p + 4 <= n:
        hdr = struct.unpack_from('<I', body, p)[0]
        p += 4
        tag, size = hdr & 0x3FF, (hdr >> 20) & 0xFFF
        if size == 0xFFF:                                   # 크기가 넘치면 다음 4바이트가 실제 크기
            size = struct.unpack_from('<I', body, p)[0]
            p += 4
        rec = body[p:p + size]
        p += size
        if tag != HWPTAG_PARA_TEXT:
            continue
        chars, i, m = [], 0, len(rec) - 1
        while i < m:
            c = struct.unpack_from('<H', rec, i)[0]
            if c in (0, 10, 13):
                chars.append('\n')
                i += 2
            elif c in CTRL_EXTENDED:
                i += 16
            elif c in CTRL_INLINE:
                i += 2
            elif c == 9:
                chars.append('\t')
                i += 2
            else:
                chars.append(chr(c))
                i += 2
        text = ''.join(chars).strip()
        if text:
            out.append(text)
    return out


def from_hwp(data):
    st = read_cfb(data)
    head = st.get('FileHeader', b'')
    if head[:17] != b'HWP Document File':
        raise ValueError('HWP 5.x 가 아니다. 3.x 이하는 포맷이 완전히 다르다')
    ver = struct.unpack_from('<BBBB', head, 32)
    flags = struct.unpack_from('<I', head, 36)[0]
    compressed, encrypted = bool(flags & 1), bool(flags & 2)
    if encrypted:
        raise ValueError('암호화된 문서다. 한글에서 열어 암호를 풀고 다시 저장해야 한다')
    lines = []
    for name in sorted(k for k in st if k.startswith('Section')):
        raw = st[name]
        lines += hwp_paragraphs(zlib.decompress(raw, -15) if compressed else raw)
    return 'hwp %d.%d.%d.%d' % (ver[3], ver[2], ver[1], ver[0]), lines


# ────────────────────────────────────────────────────────────── ZIP + XML 계열

TAG = re.compile(r'<[^>]+>')
ENTITY = [('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&apos;', "'"), ('&amp;', '&')]


def unescape(s):
    for a, b in ENTITY:
        s = s.replace(a, b)
    return s


def texts(xml, tag):
    """<tag ...>글자</tag> 를 순서대로 모은다."""
    pat = re.compile(r'<%s(?:\s[^>]*)?>(.*?)</%s>' % (tag, tag), re.S)
    return [unescape(TAG.sub('', m)) for m in pat.findall(xml)]


def numbered(zf, prefix, suffix):
    """slide1.xml, slide10.xml 이 사전순으로 뒤집히지 않게 번호로 정렬한다."""
    got = [n for n in zf.namelist() if n.startswith(prefix) and n.endswith(suffix)]
    return sorted(got, key=lambda n: int((re.findall(r'(\d+)', n) or ['0'])[-1]))


def from_hwpx(zf):
    lines = []
    for name in numbered(zf, 'Contents/section', '.xml'):
        xml = zf.read(name).decode('utf-8', 'replace')
        lines += [t for t in texts(xml, 'hp:t') if t.strip()]
    return 'hwpx', lines


def from_pptx(zf):
    lines = []
    for i, name in enumerate(numbered(zf, 'ppt/slides/slide', '.xml'), 1):
        xml = zf.read(name).decode('utf-8', 'replace')
        body = [t for t in texts(xml, 'a:t') if t.strip()]
        if body:
            lines.append('## 슬라이드 %d' % i)
            lines += body
    return 'pptx', lines


def from_xlsx(zf):
    shared = []
    if 'xl/sharedStrings.xml' in zf.namelist():
        xml = zf.read('xl/sharedStrings.xml').decode('utf-8', 'replace')
        shared = [''.join(texts(si, 't')) for si in
                  re.findall(r'<si(?:\s[^>]*)?>(.*?)</si>', xml, re.S)]
    names = {}
    if 'xl/workbook.xml' in zf.namelist():
        xml = zf.read('xl/workbook.xml').decode('utf-8', 'replace')
        for i, m in enumerate(re.findall(r'<sheet\s[^>]*name="([^"]*)"', xml), 1):
            names[i] = unescape(m)
    lines = []
    for i, name in enumerate(numbered(zf, 'xl/worksheets/sheet', '.xml'), 1):
        xml = zf.read(name).decode('utf-8', 'replace')
        rows = []
        for row in re.findall(r'<row(?:\s[^>]*)?>(.*?)</row>', xml, re.S):
            cells = []
            for attrs, inner in re.findall(r'<c\s([^>]*?)/?>(?:(.*?)</c>)?', row, re.S):
                vals = texts(inner or '', 'v') or texts(inner or '', 't')
                if not vals:
                    continue
                v = vals[0]
                if 't="s"' in attrs and v.isdigit() and int(v) < len(shared):
                    v = shared[int(v)]
                cells.append(v)
            if any(c.strip() for c in cells):
                rows.append('\t'.join(cells))
        if rows:
            lines.append('## 시트 %s' % names.get(i, i))
            lines += rows
    return 'xlsx', lines


# ─────────────────────────────────────────────────────────────────────── 실행

# 서식(표·슬라이드 배치)이 사라지는 형식
LAYOUT_LOST = {'hwpx', 'pptx', 'xlsx'}


def main():
    if len(sys.argv) < 2:
        print('사용법: python3 extract.py "파일"', file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, 'rb') as fp:
        data = fp.read()

    if data[:8] == CFB_MAGIC:
        kind, lines = from_hwp(data)
    elif data[:2] == b'PK':
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        if any(n.startswith('Contents/section') for n in names):
            kind, lines = from_hwpx(zf)
        elif any(n.startswith('ppt/slides/slide') for n in names):
            kind, lines = from_pptx(zf)
        elif any(n.startswith('xl/worksheets/sheet') for n in names):
            kind, lines = from_xlsx(zf)
        else:
            raise ValueError('아는 형식이 아니다 (ZIP 안에 hwpx/pptx/xlsx 구조가 없다)')
    else:
        raise ValueError('아는 형식이 아니다 (CFB 도 ZIP 도 아니다)')

    lost = 'yes' if (kind.startswith('hwp ') or kind in LAYOUT_LOST) else 'no'
    print('# 형식: %s' % kind)
    print('# 서식소실: %s' % lost)
    print('# 문단수: %d' % len(lines))
    print()
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:                                # 조용히 죽지 않는다
        print('!! 뽑지 못했다: %s' % exc, file=sys.stderr)
        sys.exit(1)
