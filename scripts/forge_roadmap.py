"""Forge Mentor — the plan as a page you can open.

The terminal roadmap is the one that gates the build: it is in front of the
user at the moment they accept the plan, and it needs nothing but a terminal.
This is the other half of the same view — the one that survives the scrollback,
that a mentor or a teammate can be sent, and that is still there in week six
when nobody remembers what phase four was for.

**Self-contained, deliberately.** One file, no stylesheet, no script tag
pointing anywhere, no font from a CDN. It opens from disk with a double click
on a machine with no network, which is the same stance the plugin takes about
its own dependencies — and the same reason the generated page can be committed
to the project repository without dragging anything in behind it.

It is generated from `.claude/forge/phases/` and the decision records, never
written by hand. A roadmap maintained by hand disagrees with the files within a
week, and the one that is wrong is always the one someone is reading.
"""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

import forge_state as fs
import forge_steps as st

PAGE = "roadmap.html"

# The six meanings, as CSS custom properties. Taken from the same table the
# terminal uses (rule R11) rather than re-picked here — two palettes drifting
# apart is how a product ends up meaning two different things by "yellow".
_PALETTE = {
    "AMBER": "#ffaf5f",
    "BLUE": "#5fafff",
    "GREEN": "#87d787",
    "YELLOW": "#ffd75f",
    "RED": "#ff5f5f",
    "PURPLE": "#d7afff",
}


def _e(text: object) -> str:
    """Escape anything going into the page.

    Every string here comes from a file the user has edited — a phase title, a
    step, the text of their own decision. Any of them can contain `<`, and a
    roadmap that renders a project's own notes as markup is a stored-XSS hole
    in a file the user is told to open in a browser. The security floor applies
    to the tools Forge generates, not only to the code it writes for you.
    """
    return html.escape(str(text or ""), quote=True)


def _phase_card(phase: st.Phase, decisions: dict[str, fs.Decision]) -> str:
    state = phase.state()
    steps = phase.steps
    total = len(steps)
    done = phase.built
    percent = int(round(100 * done / total)) if total else 0

    rows = []
    for step in steps:
        decision = decisions.get(step.marker)
        mark = "✅" if step.built else ("◆" if decision else "○")
        detail = ""
        if decision:
            detail = (
                f'<p class="why"><span class="label">decided</span> '
                f"{_e(decision.question)}</p>"
            )
        rows.append(
            f'<li class="step {"built" if step.built else ""}">'
            f'<span class="mark">{mark}</span>'
            f'<span class="text">{_e(step.text)}</span>{detail}</li>'
        )

    steps_html = (
        f'<ol class="steps">{"".join(rows)}</ol>'
        if rows
        else '<p class="empty">Not broken into steps yet. '
        "Forge asks about each one before it is written.</p>"
    )

    return f"""
    <article class="phase {state}">
      <header>
        <span class="num">{_e(phase.number)}</span>
        <h2>{_e(phase.title)}</h2>
        <span class="badge">{state}</span>
      </header>
      <p class="delivers">{_e(phase.delivers)}</p>
      <div class="bar" role="img" aria-label="{done} of {total} steps built">
        <span style="width:{percent}%"></span>
      </div>
      <p class="count">{done} of {total} steps built</p>
      {steps_html}
    </article>"""


def render(forge_dir: Path, project: str = "") -> str:
    """The page, as a string."""
    phases = st.roadmap(forge_dir)

    by_marker: dict[str, fs.Decision] = {}
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        for token in (decision.affects or "").replace(",", " ").split():
            if token.startswith("phase-") and ".step-" in token:
                by_marker[token] = decision

    built, total = st.position(forge_dir)
    accepted = st.plan_accepted(forge_dir)
    cards = "".join(_phase_card(p, by_marker) for p in phases)

    variables = "\n".join(f"      --{k.lower()}: {v};" for k, v in _PALETTE.items())

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(project or "Forge")} — the plan</title>
<style>
  :root {{
{variables}
    --ink: #e8e6e3;
    --quiet: #9b9691;
    --faint: #4a4643;
    --page: #16130f;
    --card: #1f1b16;
    color-scheme: dark light;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --ink: #241f19; --quiet: #6b645c; --faint: #cfc7bd;
      --page: #faf7f2; --card: #fff;
      --amber: #b06a00; --blue: #0b62b8; --green: #2f7d32;
      --yellow: #8a6a00; --red: #b3261e; --purple: #6f42c1;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2.5rem 1.25rem 5rem;
    background: var(--page); color: var(--ink);
    font: 16px/1.6 ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
  }}
  main {{ max-width: 46rem; margin: 0 auto; }}
  .mast {{ display: flex; align-items: baseline; gap: .75rem; flex-wrap: wrap;
           border-bottom: 1px solid var(--faint); padding-bottom: 1rem; }}
  .mast h1 {{ font-size: 1.35rem; margin: 0; letter-spacing: -.01em; }}
  .mark {{ color: var(--amber); }}
  .mast .tag {{ color: var(--quiet); font-size: .85rem; }}
  .summary {{ color: var(--quiet); font-size: .9rem; margin: 1rem 0 2rem; }}
  .summary strong {{ color: var(--ink); }}
  .pending {{ color: var(--yellow); }}

  .phase {{
    position: relative; background: var(--card);
    border: 1px solid var(--faint); border-left: 3px solid var(--faint);
    border-radius: .5rem; padding: 1.1rem 1.25rem; margin: 0 0 1rem;
  }}
  .phase.done {{ border-left-color: var(--green); }}
  .phase.now  {{ border-left-color: var(--amber); }}
  .phase header {{ display: flex; align-items: center; gap: .7rem; }}
  .phase h2 {{ font-size: 1rem; margin: 0; flex: 1; }}
  .num {{ color: var(--quiet); font-variant-numeric: tabular-nums; }}
  .badge {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
            color: var(--quiet); }}
  .done .badge {{ color: var(--green); }}
  .now .badge {{ color: var(--amber); }}
  .delivers {{ color: var(--quiet); margin: .5rem 0 .9rem; font-size: .92rem; }}

  .bar {{ height: 4px; background: var(--faint); border-radius: 2px; overflow: hidden; }}
  .bar span {{ display: block; height: 100%; background: var(--green); }}
  .count {{ font-size: .78rem; color: var(--quiet); margin: .4rem 0 0; }}

  .steps {{ list-style: none; margin: .9rem 0 0; padding: 0; }}
  .step {{ display: grid; grid-template-columns: 1.4rem 1fr; gap: .4rem .5rem;
           padding: .35rem 0; font-size: .92rem; }}
  .step .mark {{ color: var(--faint); }}
  .step.built .mark {{ color: var(--green); }}
  .step.built .text {{ color: var(--quiet); }}
  .why {{ grid-column: 2; margin: .2rem 0 0; font-size: .8rem; color: var(--quiet); }}
  .label {{ color: var(--blue); }}
  .empty {{ font-size: .85rem; color: var(--quiet); margin: .8rem 0 0; }}

  footer {{ margin-top: 2.5rem; color: var(--faint); font-size: .78rem; }}
</style>
</head>
<body>
<main>
  <div class="mast">
    <h1><span class="mark">⚒</span> {_e(project or "This project")}</h1>
    <span class="tag">the whole plan · {len(phases)} phases</span>
  </div>

  <p class="summary">
    <strong>{built} of {total} steps built.</strong>
    Every step was a question before it was code, and every answer is in
    <code>.claude/forge/decisions/</code>.
    {"" if accepted else '<br><span class="pending">This plan has not been accepted yet — nothing is being built.</span>'}
  </p>

  {cards}

  <footer>
    Generated by Forge Mentor on {date.today().isoformat()} from
    <code>.claude/forge/</code>. Regenerated whenever the plan changes — edit
    the phase files, not this page.
  </footer>
</main>
</body>
</html>
"""


def write(forge_dir: Path, project: str = "") -> Path:
    """Generate the page and say where it went."""
    path = forge_dir / PAGE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(forge_dir, project), encoding="utf-8")
    return path
