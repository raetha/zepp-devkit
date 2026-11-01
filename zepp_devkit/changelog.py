"""Keep a Changelog files: one version's section, and that section as HTML."""
import html
import re
from pathlib import Path


def section(path, version):
    """The body of `## [version]` in a CHANGELOG.md ("Unreleased" works too); None if absent."""
    path = Path(path)
    if not path.exists():
        return None
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", path.read_text(), re.S | re.M)
    return m.group(1).strip() if m else None


def _inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)


def to_html(markdown):
    """A changelog section as HTML: paragraphs, ### headings and - bullets (all it uses)."""
    out, para, items = [], [], []

    def flush():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in markdown.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("### "):
            flush()
            out.append(f"<h4>{_inline(s[4:])}</h4>")
        elif s.startswith("- "):
            if para:
                flush()
            items.append(s[2:])
        elif items:
            items[-1] += " " + s  # a bullet continued on the next line
        else:
            para.append(s)
    flush()
    return "\n".join(out)
