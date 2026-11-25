#!/usr/bin/env python3
"""Build the per-section pages (missions/, platforms/, ...) from index.html.

These pages exist so Google can show sitelinks under atsmus.com. Each one
reuses the exact markup, styles and scripts of its section on the homepage,
so the design and text stay identical. index.html is the only file to edit:
after changing it, run  `python3 tools/build_section_pages.py`  from the repo
root and commit the regenerated folders together with index.html.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://atsmus.com"

# section id on the homepage -> (folder / URL slug, short name, search title, meta description)
# The search title and description only show in Google results and the browser tab.
PAGES = {
    "missions": (
        "missions",
        "Missions",
        "Drone Navigation Through Jamming & Counter-UAS Missions | ATSMUS",
        "GPS-denied navigation for DoD tactical UAS that holds through jamming and spoofing, "
        "passive drone detection for DHS and border security, and perimeter protection for bases.",
    ),
    "platform": (
        "platforms",
        "Platforms",
        "GPS-Denied Navigation & Passive C-UAS Radar Platforms | ATSMUS",
        "ATSMUS AIR cellular GPS-denied navigation payload, ATSMUS PDDR passive bistatic "
        "counter-UAS radar, SENTINEL IMSI-catcher detection and the AIRT RF planning engine.",
    ),
    "trials": (
        "flight-heritage",
        "Flight Heritage",
        "GPS-Denied Navigation Flight Test Results | ATSMUS AeroTech",
        "Live-flight proof of GPS-denied drone navigation: a GNSS-grade one-hour rotary outage "
        "test, a 400 km alpine corridor at 4,000 m, and anchorless cellular navigation.",
    ),
    "leadership": (
        "leadership",
        "Leadership",
        "Leadership & Board of Advisors | ATSMUS AeroTech",
        "The ATSMUS team behind cellular positioning and passive radar, and its Board of Advisors: "
        "MG (Ret.) William Grimsley and former OSD Pentagon strategist Ian Saltz.",
    ),
    "contact": (
        "contact",
        "Contact & Request Access",
        "Request an Evaluation Kit | ATSMUS AeroTech",
        "Request an ATSMUS evaluation kit or Technical Data Package for GPS-denied navigation and "
        "passive counter-UAS detection. Designed to meet NDAA and Blue UAS requirements. CAGE 25JJ8.",
    ),
}

# Extra blocks that belong with a section (e.g. the bio modal opened from Leadership).
EXTRA_BLOCKS = {
    "leadership": [
        r'  <!-- =+\s*GRIMSLEY FULL BIO MODAL.*?(?=\n  <!-- =+)',
        r'  <!-- =+\s*IAN SALTZ FULL BIO MODAL.*?(?=\n  <!-- =+)',
    ],
}

# Script blocks of the homepage and the element each one needs. A block whose
# element is not on the page is left out, so it can't throw or waste CPU.
SCRIPT_NEEDS = {
    "IAN SALTZ FULL BIO MODAL": "ianBioModal",
    "HERO ROTATING HEADLINES": "rotatingHeadline",
    "3D DEFENSE DRONE": "threeHeroCanvas",
    "CONTINUOUS 3D TACTICAL STEALTH DRONE": "missionsPanoramaContainer",
    "CAROUSEL AUTO-ADVANCE": "carouselWrapper",
    "MOTION SERVICE GRAPHICS": "serviceCanvas",
}

MARKER = re.compile(r"\n    // -{20,}\n    // (.*?)\n    // -{20,}\n")


def attr(text: str) -> str:
    return html.escape(text, quote=True)


def set_meta(head: str, pattern: str, value: str) -> str:
    new, n = re.subn(pattern, lambda m: m.group(1) + attr(value) + m.group(2), head, count=1)
    assert n == 1, pattern
    return new


def build_head(head: str, slug: str, name: str, title: str, desc: str) -> str:
    url = f"{SITE}/{slug}/"
    head = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", head, count=1)
    head = set_meta(head, r'(<meta name="description" content=")[^"]*(" />)', desc)
    head = set_meta(head, r'(<meta property="og:title" content=")[^"]*(" />)', title)
    head = set_meta(head, r'(<meta property="og:description" content=")[^"]*(" />)', desc)
    head = head.replace(f'<link rel="canonical" href="{SITE}/" />', f'<link rel="canonical" href="{url}" />')
    head = head.replace(f'<meta property="og:url" content="{SITE}/" />', f'<meta property="og:url" content="{url}" />')
    # The full organization data stays on the homepage; each section page describes itself
    # and its place in the site (shown by Google as "atsmus.com > Platforms").
    page_ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": url,
                "url": url,
                "name": title,
                "description": desc,
                "isPartOf": {"@id": f"{SITE}/#website"},
                "about": {"@id": f"{SITE}/#organization"},
                "breadcrumb": {"@id": url + "#breadcrumb"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "ATSMUS", "item": f"{SITE}/"},
                    {"@type": "ListItem", "position": 2, "name": name, "item": url},
                ],
            },
        ],
    }
    ld = json.dumps(page_ld, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    head = re.sub(
        r'  <script type="application/ld\+json">.*?</script>',
        lambda m: '  <script type="application/ld+json">\n  ' + ld + "\n  </script>",
        head, count=1, flags=re.S,
    )
    return head


def split_script(script_body: str):
    """Yield (label, code) chunks of the main homepage script."""
    parts = MARKER.split(script_body)
    yield "PREAMBLE", parts[0]
    for i in range(1, len(parts), 2):
        yield parts[i], parts[i + 1]


def main():
    src = (ROOT / "index.html").read_text(encoding="utf-8")

    head_end = src.index("</head>")
    head = src[:head_end]
    body = src[head_end:]

    header = re.search(r"\n  <!-- =+\s*1\. NAVIGATION.*?</header>\n", body, re.S).group(0)
    body_open = body[: body.index(header)]
    footer = re.search(r"\n  <!-- =+\s*10\. STREAMLINED MINIMALIST FOOTER.*?</footer>\n", body, re.S).group(0)
    main_script_match = re.search(
        r"(\n  <!-- =+\s*JAVASCRIPT:.*?=+ -->\n  <script>)(.*?)(\n  </script>)", body, re.S
    )
    trailing = body[main_script_match.end():]  # nav click handler + </body></html>

    for sid, (slug, name, title, desc) in PAGES.items():
        section = re.search(rf"\n *<!-- =+[^>]*-->\n  <section id=\"{sid}\".*?</section>\n", body, re.S)
        assert section, sid
        content = section.group(0)
        for pat in EXTRA_BLOCKS.get(sid, []):
            content += "\n" + re.search(pat, body, re.S).group(0) + "\n"

        page_body = header + "\n  <!-- Spacer under the fixed header -->\n" \
            '  <div class="h-16 sm:h-20" aria-hidden="true"></div>\n' + content + footer

        ids = set(re.findall(r'\sid="([^"]+)"', page_body))

        # Menu links: the current section scrolls in place, the rest go back to the homepage.
        def nav_link(m):
            target = m.group(2)
            if target == sid:
                return f'<a href="#{target}" class='
            return f'<a href="/#{target}" class='
        page_body = re.sub(r'<a href="(/[a-z-]+/)" data-section="([a-z]+)" class=', nav_link, page_body)

        # Logo links and in-section links to sections that live on the homepage.
        page_body = page_body.replace('<a href="#" class=', '<a href="/" class=')

        def fix_anchor(m):
            target = m.group(1)
            if target in ids:
                return m.group(0)
            return f'href="/#{target}"'
        page_body = re.sub(r'href="#([A-Za-z][\w-]*)"', fix_anchor, page_body)
        # Platform shortcuts on the Missions cards just go to the homepage platform section.
        if "carouselWrapper" not in ids:
            page_body = re.sub(r'(href="/#platform") onclick="explorePlatform\(\d\)"', r"\1", page_body)

        # Relative file paths (e.g. src="Ian.png") must point at the site root from a subfolder.
        page_body = re.sub(r'\b(src|poster)="(?![a-z]+:|/|#)([^"]+)"', r'\1="/\2"', page_body)

        # Scripts: keep only the blocks whose elements exist on this page, each in its own tag.
        chunks = []
        for label, code in split_script(main_script_match.group(2)):
            need = next((el for key, el in SCRIPT_NEEDS.items() if key in label), None)
            if need and need not in ids:
                continue
            chunks.append(code.strip("\n"))
        scripts = (
            "\n  <!-- Scripts from the homepage, limited to what this section uses -->\n  <script>\n"
            + "\n\n".join(chunks)
            + "\n  </script>"
        )

        page_head = build_head(head, slug, name, title, desc)
        if "threeHeroCanvas" not in ids and "missionsPanoramaContainer" not in ids:
            page_head = re.sub(
                r'\n  <!-- Three\.js[^\n]*-->\n  <script src="[^"]*three[^"]*"></script>\n', "\n", page_head
            )

        doctype, rest = page_head.split("\n", 1)  # the doctype must stay on the first line
        out = (
            doctype
            + "\n<!-- Generated from index.html by tools/build_section_pages.py: edit index.html, then rerun. -->\n"
            + rest + body_open + page_body + scripts + trailing
        )
        dest = ROOT / slug / "index.html"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        print(f"built /{slug}/  ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
