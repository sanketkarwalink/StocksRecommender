import datetime as dt
from pathlib import Path
from typing import List

from engine.sip_allocator import SIPAction


def render_report(actions: List[SIPAction], regime_cautious: bool) -> str:
    lines = []
    lines.append(f"SIP Report: {dt.date.today()}")
    lines.append(f"Market regime cautious: {'YES' if regime_cautious else 'NO'}")
    lines.append("")
    header = f"{'Ticker':8s} {'Name':18s} {'Sector':12s} {'Score':>6s} {'Valuation':12s} {'Trend':10s} {'Mult':>5s} {'SIP':>8s} Notes"
    lines.append(header)
    lines.append("-" * len(header))
    for a in actions:
        lines.append(
            f"{a.ticker:8s} {a.name[:18]:18s} {a.sector[:12]:12s} "
            f"{a.fundamental_score:6.1f} {a.valuation:12s} {a.trend_state:10s} "
            f"{a.allocation_multiplier:5.2f} {a.recommended_sip:8.0f} {a.notes}"
        )
    return "\n".join(lines)


def save_report(text: str, cfg: dict) -> Path:
    out_dir = Path(cfg["reporting"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"sip-report-{ts}.txt"
    path.write_text(text)
    return path
