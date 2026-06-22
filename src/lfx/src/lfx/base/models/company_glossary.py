"""Instance-wide company glossary injection for system prompts.

When ``LANGFLOW_COMPANY_GLOSSARY`` is set, its value is prepended to the system
prompt of every Agent and Language Model component at build time. This lets an
operator teach the LLM about company-internal terms (messengers, ERP systems,
internal jargon) without editing each flow or component on the canvas.

The injection is unconditional: a user cannot disable it by clearing the
``system_message`` / ``system_prompt`` field on a component, because the
prepend happens after the user's text is read. This is intentional — the
glossary is part of the platform contract, not a per-flow tuneable.

Usage:
    # docker-compose.yml
    environment:
      - LANGFLOW_COMPANY_GLOSSARY=|
          You are an internal assistant for Nimbus Semiconductor.
          - PULSE: internal company messenger
          - ATLAS: ERP system

If the env var is unset or empty the helper is a no-op.

``EXAMPLE_COMPANY_GLOSSARY`` below is published as a copy-pasteable starting
point. The names are intentionally fictional (Nimbus, PULSE, ATLAS, …) so the
example can ship without revealing any real company's internal taxonomy.
"""

from __future__ import annotations

import os

_ENV_VAR = "LANGFLOW_COMPANY_GLOSSARY"

# Fictional names — replace with your own organization's terminology.
EXAMPLE_COMPANY_GLOSSARY = """\
You are an internal assistant for Nimbus Semiconductor. The following
company-internal terms must always be interpreted with these meanings:

- PULSE — internal company messenger (Slack equivalent)
- ATLAS — ERP system used for finance and procurement
- MOSAIC — HR information system (employee records, leave, payroll)
- BEACON — internal knowledge base / wiki
- SENTINEL — release quality-review process
- ORBIT — internal CI/CD pipeline
- HORIZON — quarterly long-term roadmap planning workshop

When the user mentions these terms, interpret them according to the
definitions above unless context clearly indicates otherwise."""


def get_company_glossary() -> str:
    """Return the configured glossary string, or empty if unset.

    The value is read fresh on every call so an operator can change the env
    var and restart the worker without rebuilding the image. The cost is
    negligible (one ``os.environ`` lookup) compared to a single LLM call.
    """
    return (os.environ.get(_ENV_VAR) or "").strip()


def prepend_company_glossary(system_text: str | None) -> str | None:
    """Prepend the company glossary to *system_text*.

    Returns the original ``system_text`` unchanged when no glossary is
    configured. When a glossary is present:

    - ``None`` or empty ``system_text`` → returns just the glossary.
    - Non-empty ``system_text`` → returns ``"<glossary>\\n\\n<system_text>"``.

    The glossary lives at the *top* so the LLM sees it before any flow-author
    instructions. This matches the conventional system-prompt structure
    (identity / persona → task instructions).
    """
    glossary = get_company_glossary()
    if not glossary:
        return system_text
    if not system_text:
        return glossary
    return f"{glossary}\n\n{system_text}"
