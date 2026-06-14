"""Terminal output formatting using ASCII-safe characters."""

import pandas as pd

# Use plain print instead of Rich to avoid encoding issues on Windows
# Rich console with emoji is problematic on GBK terminals


def print_header(title: str, subtitle: str = ""):
    """Print a formatted header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * 60)
    print()


def print_success(msg: str):
    print(f"  [OK] {msg}")


def print_warning(msg: str):
    print(f"  [WARN] {msg}")


def print_error(msg: str):
    print(f"  [ERROR] {msg}")


def print_info(msg: str):
    print(f"  [INFO] {msg}")


def format_number(val, fmt: str = ".2f", prefix: str = "") -> str:
    """Format a number with optional prefix."""
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{float(val):{fmt}}"
    except (ValueError, TypeError):
        return str(val)


def format_pct(val, decimal: int = 1) -> str:
    """Format a percentage value."""
    if val is None:
        return "N/A"
    try:
        sign = "+" if float(val) >= 0 else ""
        return f"{sign}{float(val)*100:.{decimal}f}%"
    except (ValueError, TypeError):
        return str(val)


def format_cny(val) -> str:
    """Format a CNY amount."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e8:
            return f"CNY{val/1e8:.2f}yi"
        elif abs(val) >= 1e4:
            return f"CNY{val/1e4:.2f}wan"
        else:
            return f"CNY{val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def format_cell(val) -> str:
    """Format a cell value for display."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "-"
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:,.2f}"
        elif abs(val) >= 1:
            return f"{val:.2f}"
        elif abs(val) >= 0.01:
            return f"{val:.4f}"
        elif abs(val) > 0:
            return f"{val:.6f}"
        else:
            return f"{val:.2f}"
    return str(val)


def portfolio_summary_table(summary: dict) -> str:
    """Generate a formatted portfolio summary string."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  [Portfolio] {summary.get('portfolio_name', 'N/A')}")
    lines.append("=" * 70)
    lines.append(f"  Risk Profile: {summary.get('risk_profile', 'N/A')}")
    lines.append(f"  Initial Capital: {format_cny(summary.get('initial_capital', 0))}")
    lines.append(f"  Current Value:   {format_cny(summary.get('current_value', 0))}")
    total_return = summary.get('total_return', 0)
    sign = "+" if total_return >= 0 else ""
    lines.append(f"  Total Return:    {sign}{total_return*100:.2f}%")
    lines.append(f"  Total P&L:       {format_cny(summary.get('total_pnl', 0))}")
    lines.append(f"  Holdings Count:  {summary.get('holdings_count', 0)}")
    lines.append("")

    # Holdings table
    holdings = summary.get("holdings", [])
    if holdings:
        lines.append("  --- Holdings ---")
        header = f"  {'Name':<20s} {'Code':<8s} {'Shares':>10s} {'Cost':>8s} {'NAV':>8s} {'MktVal':>12s} {'P&L':>8s} {'Wgt':>6s}"
        lines.append(header)
        lines.append("  " + "-" * 74)

        for h in holdings:
            name = (h.get("fund_name", "") or "")[:18]
            code = h.get("fund_code", "") or ""
            shares = f"{h.get('shares', 0):,.0f}" if h.get('shares') else "0"
            cost = f"{h.get('avg_cost', 0):.4f}" if h.get('avg_cost') else "0"
            nav = f"{h.get('current_nav', 0):.4f}" if h.get('current_nav') else "0"
            mkt_val = format_cny(h.get("market_value", 0))
            pnl_sign = "+" if h.get("pnl_pct", 0) >= 0 else ""
            pnl = f"{pnl_sign}{h.get('pnl_pct', 0)*100:.1f}%" if h.get('pnl_pct') is not None else "0%"
            weight = f"{h.get('weight', 0)*100:.1f}%" if h.get('weight') else "0%"
            lines.append(f"  {name:<20s} {code:<8s} {shares:>10s} {cost:>8s} "
                         f"{nav:>8s} {mkt_val:>12s} {pnl:>8s} {weight:>6s}")
        lines.append("  " + "-" * 74)

    # Allocation comparison
    alloc = summary.get("allocation_diff", {})
    if alloc:
        lines.append("")
        lines.append("  --- Allocation vs Target ---")
        for cat, diff in alloc.items():
            actual = diff.get("actual", 0)
            target = diff.get("target", 0)
            drift = diff.get("drift", 0)
            drift_sign = "+" if drift > 0 else ""
            bar_len = int(actual * 30)
            bar = "#" * bar_len + "." * (30 - bar_len)
            lines.append(f"  {cat:<8s} [{bar}] {actual:.0%}")
            lines.append(f"  {'':8s} Target: {target:.0%} | Drift: {drift_sign}{drift:.1%}")

    return "\n".join(lines)


def alert_summary_table(alerts: list[dict]) -> str:
    """Format alerts as a table string."""
    if not alerts:
        return "  [OK] No alerts"

    lines = ["", f"  Alerts ({len(alerts)} items):"]
    for i, alert in enumerate(alerts, 1):
        sev = alert.get("severity", "info")
        icon = {"info": "[i]", "warning": "[!]", "critical": "[!!!]"}.get(sev, "[?]")
        lines.append(f"  {i}. {icon} [{sev.upper()}] {alert.get('message', '')}")
    return "\n".join(lines)


def regime_indicator(regime_name: str, confidence: float) -> str:
    """Generate a visual regime indicator."""
    if "Bull" in regime_name:
        animal = "Bull"
    elif "Bear" in regime_name:
        animal = "Bear"
    else:
        animal = "Sideways"

    bar_len = int(confidence * 10)
    bar = "#" * bar_len + "." * (10 - bar_len)

    return f"  {animal} {regime_name} Confidence: [{bar}] {confidence:.0%}"
