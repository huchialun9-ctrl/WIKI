import re
from datetime import datetime
from typing import Optional


# 繁簡轉換對照表 (zh-tw → zh-cn)
LANG_TABLE = {
    "吸色管": "吸管",
    "畫筆": "画笔",
    "調色盤": "调色板",
    "姿勢": "姿势",
    "皮膚": "皮肤",
    "宅邸": "宅邸",
    "下水道": "下水道",
    "後室": "后室",
    "企鵝飯店": "企鹅酒店",
    "糖果屋": "糖果屋",
    "塗鴉躲貓貓": "涂鸦躲猫猫",
    "塗鴉覆蓋率": "涂鸦覆盖率",
    "碰撞體": "碰撞体",
    "獵人": "猎人",
    "躲藏者": "躲藏者",
    "吸色": "吸色",
    "冷卻時間": "冷却时间",
    "解鎖條件": "解锁条件",
    "隱藏成就": "隐藏成就",
    "工作坊": "工作坊",
    "指南": "指南",
    "地圖": "地图",
    "道具": "道具",
    "外觀": "外观",
    "消歧義": "消歧义",
}

LANG_TABLE_REVERSE = {v: k for k, v in LANG_TABLE.items()}


class WikitextParser:
    WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)(?:\|([^\[\]]+?))?\]\]")
    REF_RE = re.compile(r"<ref>([^<]+)</ref>")
    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    MAGIC_WORD_RE = re.compile(r"\{\{(\w+)(?::([^}]+))?\}\}")
    CHAMELEON_COLOR_RE = re.compile(
        r'<chameleon-color\s+code="([^"]+)"\s*/>', re.IGNORECASE
    )

    def __init__(self):
        self.footnotes = []
        self.magic_values = {}
        self.lang = "zh-tw"

    def set_magic(self, key: str, value: str):
        self.magic_values[key] = value

    def set_lang(self, lang: str):
        self.lang = lang if lang in ("zh-tw", "zh-cn") else "zh-tw"

    def parse(self, text: str) -> str:
        self.footnotes = []
        if not text:
            return ""
        html = text
        html = self._parse_headings(html)
        html = self._parse_bold_italic(html)
        html = self._parse_magic_words(html)
        html = self._parse_chameleon_color(html)
        html = self._parse_refs(html)
        html = self._parse_wikilinks(html)
        html = self._parse_lists(html)
        html = self._parse_horizontal_rules(html)
        html = self._apply_lang_conversion(html)
        html = self._wrap_paragraphs(html)
        if self.footnotes:
            html += self._render_references()
        return html

    def _parse_headings(self, text: str) -> str:
        def repl(m):
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-").lower()
            return f'<h{level} id="{anchor}">{title}</h{level}>'
        return self.HEADING_RE.sub(repl, text)

    def _parse_bold_italic(self, text: str) -> str:
        text = re.sub(r"'''(.*?)'''", r"<strong>\1</strong>", text)
        text = re.sub(r"''(.*?)''", r"<em>\1</em>", text)
        return text

    def _parse_magic_words(self, text: str) -> str:
        def repl(m):
            word = m.group(1).upper()
            if word == "NUMBEROFARTICLES":
                return self.magic_values.get("NUMBEROFARTICLES", "0")
            elif word == "REVISIONDAY":
                return self.magic_values.get(
                    "REVISIONDAY", datetime.now().strftime("%d")
                )
            elif word == "REVISIONMONTH":
                return self.magic_values.get(
                    "REVISIONMONTH", datetime.now().strftime("%m")
                )
            elif word == "CURRENTVERSION":
                return self.magic_values.get("CURRENTVERSION", "?")
            elif word == "SITENAME":
                return "Meccha Chameleon Wiki"
            return m.group(0)
        return self.MAGIC_WORD_RE.sub(repl, text)

    def _parse_chameleon_color(self, text: str) -> str:
        def repl(m):
            hex_code = m.group(1).strip().lstrip("#")
            full_hex = f"#{hex_code}"
            rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
            return (
                f'<span class="chameleon-color-swatch" style="display:inline-flex;'
                f'align-items:center;gap:4px;margin:0 2px;">'
                f'<span class="color-swatch" style="background:{full_hex};'
                f'width:20px;height:20px;display:inline-block;'
                f'border:1px solid #a2a9b1;vertical-align:middle;'
                f'cursor:pointer;" onclick="navigator.clipboard.writeText(\'{full_hex}\')'
                f'.then(()=>showToast(\'已複製色碼：{full_hex}\'))"></span>'
                f'<span class="color-hex" data-hex="{full_hex}" '
                f'style="font-family:Consolas,monospace;cursor:pointer;'
                f'color:#3366cc;font-size:0.9em;">{full_hex}</span>'
                f'<span style="color:#54595d;font-size:0.8em;">'
                f'rgb{rgb[0]},{rgb[1]},{rgb[2]}</span>'
                f'</span>'
            )
        return self.CHAMELEON_COLOR_RE.sub(repl, text)

    def _parse_refs(self, text: str) -> str:
        def repl(m):
            idx = len(self.footnotes) + 1
            content = m.group(1).strip()
            self.footnotes.append({
                "index": idx,
                "content": content,
                "source_type": "secondary",
            })
            return (
                f'<sup class="footnote-ref" data-content="{content}">'
                f'<a href="#ref-{idx}">[{idx}]</a></sup>'
            )
        return self.REF_RE.sub(repl, text)

    def _parse_wikilinks(self, text: str) -> str:
        def repl(m):
            target = m.group(1).strip()
            display = m.group(2) if m.group(2) else target
            url = f"/{target}"
            return f'<a href="{url}">{display}</a>'
        return self.WIKILINK_RE.sub(repl, text)

    def _parse_lists(self, text: str) -> str:
        lines = text.split("\n")
        result = []
        in_ul = False
        for line in lines:
            if line.startswith("- ") or line.startswith("* "):
                if not in_ul:
                    result.append("<ul>")
                    in_ul = True
                result.append(f"<li>{line[2:]}</li>")
            else:
                if in_ul:
                    result.append("</ul>")
                    in_ul = False
                result.append(line)
        if in_ul:
            result.append("</ul>")
        return "\n".join(result)

    def _parse_horizontal_rules(self, text: str) -> str:
        return re.sub(r"^----+$", "<hr>", text, flags=re.MULTILINE)

    def _apply_lang_conversion(self, text: str) -> str:
        if self.lang == "zh-tw":
            table = LANG_TABLE_REVERSE
        else:
            table = LANG_TABLE
        for tw, cn in LANG_TABLE.items():
            if self.lang == "zh-cn":
                text = text.replace(tw, cn)
            else:
                text = text.replace(cn, tw)
        return text

    def _wrap_paragraphs(self, text: str) -> str:
        blocks = re.split(r"\n\s*\n", text)
        wrapped = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if any(block.startswith(t) for t in ("<h", "<ul", "</ul", "<hr", "<table",
                                                  "<div", "<span", "<sup")):
                wrapped.append(block)
            else:
                wrapped.append(f"<p>{block}</p>")
        return "\n".join(wrapped)

    def _render_references(self) -> str:
        lines = [
            '<section class="references-section">',
            "<h3>參考資料</h3>",
            '<ol class="references-list">',
        ]
        for fn in self.footnotes:
            lines.append(
                f'<li id="ref-{fn["index"]}">'
                f'<span class="ref-source-badge ref-source-secondary">二手文獻</span>'
                f'{fn["content"]}</li>'
            )
        lines.append("</ol>")
        lines.append("</section>")
        return "\n".join(lines)
