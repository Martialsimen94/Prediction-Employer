"""Shared chart colors for both dashboard apps — the validated default
palette from the platform's dataviz guidelines (categorical hues assigned
in fixed order, status colors reserved for risk level and never reused
elsewhere)."""

CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SEQUENTIAL_BLUE = "#256abf"

# RiskLevel low/medium/high/critical maps 1:1 onto the status palette's
# good/warning/serious/critical roles -- never reused for anything else.
RISK_LEVEL_COLORS = {
    "low": "#0ca30c",
    "medium": "#fab219",
    "high": "#ec835a",
    "critical": "#d03b3b",
}
RISK_LEVEL_ORDER = ["low", "medium", "high", "critical"]
