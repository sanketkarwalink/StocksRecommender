import json
import re
import subprocess
from pathlib import Path
from typing import List

import requests

# Telegram credentials
TELEGRAM_BOT_TOKEN = "8454001848:AAF16SeyNp9sLdOWUDkegt8zTDz3QWOmQqM"
TELEGRAM_CHAT_ID = "1254966299"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Paths
REPORTS_DIR = Path("reports")
HOLDINGS_FILE = Path("data/holdings.yaml")


def run_portfolio_tool() -> Path:
    """Run portfolio_tool.py and return path to latest report."""
    result = subprocess.run(
        ["/Users/sanketkarwa/PortfolioTracker/.venv/bin/python", "portfolio_tool.py"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"portfolio_tool.py failed: {result.stderr}")
    
    # Find latest report
    reports = sorted(REPORTS_DIR.glob("report-*.txt"))
    if not reports:
        raise RuntimeError("No reports found after running portfolio_tool.py")
    return reports[-1]


def extract_detailed_actions(report_path: Path) -> str:
    """Extract detailed sell/buy instructions from report."""
    text = report_path.read_text()
    lines = text.split("\n")
    
    # Find the detailed sections
    detailed_start = -1
    for i, line in enumerate(lines):
        if "DETAILED SELL/TRIM INSTRUCTIONS:" in line:
            detailed_start = i
            break
    
    if detailed_start == -1:
        # Fallback to TLDR if no detailed section
        return extract_tldr_fallback(lines)
    
    # Extract from detailed section to end of cash summary
    detailed_lines = []
    for i in range(detailed_start, len(lines)):
        line = lines[i]
        if "Momentum short-list" in line:
            break
        detailed_lines.append(line)
    
    return "\n".join(detailed_lines).strip()


def extract_tldr_fallback(lines: List[str]) -> str:
    """Fallback: extract TLDR section."""
    tldr_lines = []
    in_tldr = False
    for line in lines:
        if line.strip().startswith("TLDR:"):
            in_tldr = True
            continue
        if in_tldr:
            if line.strip() == "" or (line and not line.startswith("-")):
                break
            if line.startswith("- "):
                tldr_lines.append(line[2:].strip())
    return "\n".join(f"• {item}" for item in tldr_lines)


def send_telegram_alert(detailed_text: str, report_path: Path) -> None:
    """Send Telegram message with detailed actions."""
    if not detailed_text or "No actions" in detailed_text:
        return  # Skip if no actions
    
    # Format for Telegram with monospace formatting for better readability
    msg = "📊 *Portfolio Alert* 📊\n\n"
    msg += f"`{detailed_text}`"
    msg += f"\n\n📄 Full report: `{report_path.name}`"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
    }
    
    try:
        resp = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✓ Telegram alert sent with detailed instructions")
        else:
            print(f"✗ Telegram send failed: {resp.text}")
    except Exception as e:
        print(f"✗ Telegram error: {e}")


def main() -> None:
    try:
        print("Running portfolio analysis...")
        report_path = run_portfolio_tool()
        print(f"Report saved: {report_path}")
        
        detailed_text = extract_detailed_actions(report_path)
        print(f"Extracted detailed actions ({len(detailed_text)} chars)")
        
        if detailed_text:
            send_telegram_alert(detailed_text, report_path)
        else:
            print("No actions to alert on.")
    except Exception as e:
        print(f"Error: {e}")
        # Optionally send error alert
        error_msg = f"❌ Portfolio alert failed: {str(e)}"
        requests.post(
            TELEGRAM_API,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": error_msg},
            timeout=10,
        )


if __name__ == "__main__":
    main()
