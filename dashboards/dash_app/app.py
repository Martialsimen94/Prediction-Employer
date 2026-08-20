"""Executive and Data Scientist dashboards (Module 11). Everything renders
from the backend REST API (Modules 4-11) via dashboards/common/api_client.py
— no direct database access. The access token lives in a browser
session-storage `dcc.Store`, not server memory, since Dash has no built-in
per-user server session.

    PYTHONPATH=dashboards poetry run python dashboards/dash_app/app.py
"""

import os
from typing import Any

import dash
import pandas as pd
import plotly.express as px
from common.api_client import ApiError, ApiSession, get, login, post
from common.colors import RISK_LEVEL_COLORS, RISK_LEVEL_ORDER, SEQUENTIAL_BLUE
from dash import Input, Output, State, dash_table, dcc, html, no_update

app = dash.Dash(__name__, title="Retention Platform", suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    [dcc.Store(id="session-store", storage_type="session"), html.Div(id="page-content")]
)


def _session_from_store(data: dict[str, Any] | None) -> ApiSession | None:
    if not data:
        return None
    return ApiSession(
        base_url=data["base_url"], access_token=data["access_token"], user=data["user"]
    )


def _stat_card(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, style={"color": "#52514e", "fontSize": "13px"}),
            html.Div(value, style={"fontSize": "28px", "fontWeight": 600}),
        ],
        style={
            "border": "1px solid #e1e0d9",
            "borderRadius": "8px",
            "padding": "12px 16px",
            "flex": 1,
        },
    )


def _data_table(rows: list[dict[str, Any]], columns: list[str]) -> dash_table.DataTable:
    # DataTable validates every key of every row dict, not just the ones
    # named in `columns` -- a nested value elsewhere in the row (e.g.
    # top_features, a dict) fails validation even though it's never
    # rendered, so rows must be pre-filtered down to just these columns.
    filtered_rows = [{column: row[column] for column in columns} for row in rows]
    return dash_table.DataTable(
        data=filtered_rows,
        columns=[{"name": column, "id": column} for column in columns],
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "6px", "fontFamily": "system-ui, sans-serif"},
        style_header={"fontWeight": 600},
        sort_action="native",
    )


def _login_layout(error: str | None = None) -> html.Div:
    return html.Div(
        [
            html.H1("AI Employee Retention Platform"),
            html.P("Executive and Data Scientist dashboards"),
            dcc.Input(
                id="login-email",
                type="email",
                value="",
                placeholder="Email",
                style={"display": "block", "marginBottom": "8px", "width": "100%"},
            ),
            dcc.Input(
                id="login-password",
                type="password",
                value="",
                placeholder="Password",
                style={"display": "block", "marginBottom": "8px", "width": "100%"},
            ),
            html.Button("Log in", id="login-button"),
            html.Div(error or "", id="login-error", style={"color": "#d03b3b", "marginTop": "8px"}),
        ],
        style={"maxWidth": "320px", "margin": "80px auto"},
    )


def _executive_view(session: ApiSession) -> html.Div:
    kpis = get(session, "/reports/department-kpis")
    if not kpis:
        return html.P("No departments on record yet.")
    kpi_df = pd.DataFrame(kpis)

    total_headcount = int(kpi_df["active_headcount"].sum())
    total_terminations = int(kpi_df["terminations_last_12_months"].sum())
    turnover = round(total_terminations / max(total_headcount, 1) * 100, 2)

    headcount_fig = px.bar(
        kpi_df,
        x="department_name",
        y="active_headcount",
        title="Headcount by department",
        color_discrete_sequence=[SEQUENTIAL_BLUE],
    )
    headcount_fig.update_layout(xaxis_title=None, yaxis_title="Employees")

    distribution = get(session, "/reports/risk-distribution")
    risk_df = pd.DataFrame(
        {
            "risk_level": RISK_LEVEL_ORDER,
            "employees": [distribution.get(level, 0) for level in RISK_LEVEL_ORDER],
        }
    )
    risk_fig = px.pie(
        risk_df,
        names="risk_level",
        values="employees",
        color="risk_level",
        color_discrete_map=RISK_LEVEL_COLORS,
        category_orders={"risk_level": RISK_LEVEL_ORDER},
        title="Attrition risk distribution",
    )

    return html.Div(
        [
            html.Div(
                [
                    _stat_card("Active headcount", f"{total_headcount:,}"),
                    _stat_card("Terminations (12mo)", f"{total_terminations:,}"),
                    _stat_card("Company-wide turnover", f"{turnover}%"),
                ],
                style={"display": "flex", "gap": "16px", "margin": "16px 0"},
            ),
            html.Div(
                [
                    dcc.Graph(figure=headcount_fig, style={"flex": 1}),
                    dcc.Graph(figure=risk_fig, style={"flex": 1}),
                ],
                style={"display": "flex", "gap": "16px"},
            ),
        ]
    )


def _data_scientist_view(session: ApiSession) -> html.Div:
    drift = get(session, "/drift-reports", limit=50)
    risk_page = get(session, "/reports/attrition-risk-summary", limit=20)

    drift_columns = ["feature_name", "method", "drift_score", "drift_detected", "generated_at"]
    risk_columns = [
        "employee_number",
        "first_name",
        "last_name",
        "department_name",
        "risk_level",
        "risk_score",
    ]

    return html.Div(
        [
            html.Button("Run drift check now", id="drift-check-button"),
            html.Div(id="drift-check-status", style={"margin": "8px 0"}),
            html.H3("Recent drift reports"),
            _data_table(drift["items"], drift_columns),
            html.H3("Top attrition risk (company-wide)"),
            _data_table(risk_page["items"], risk_columns),
        ]
    )


_VIEWS = {
    "executive": ("Executive", _executive_view),
    "admin": ("Executive", _executive_view),
    "data_scientist": ("Data Scientist", _data_scientist_view),
}


def _dashboard_layout(session: ApiSession) -> html.Div:
    seen_labels: set[str] = set()
    tabs = []
    for role, (label, view) in _VIEWS.items():
        if session.has_role(role) and label not in seen_labels:
            seen_labels.add(label)
            tabs.append(dcc.Tab(label=label, children=view(session)))

    body: html.Div | dcc.Tabs
    if tabs:
        body = dcc.Tabs(tabs)
    else:
        body = html.P(
            "Your role doesn't have a dashboard view yet (executive or data_scientist only)."
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(f"{session.user.get('email')} — {', '.join(session.roles)}"),
                    html.Button("Log out", id="logout-button", style={"marginLeft": "16px"}),
                ],
                style={"marginBottom": "16px"},
            ),
            body,
        ]
    )


@app.callback(Output("page-content", "children"), Input("session-store", "data"))
def _render_page(data: dict[str, Any] | None) -> html.Div:
    session = _session_from_store(data)
    return _login_layout() if session is None else _dashboard_layout(session)


@app.callback(
    Output("session-store", "data"),
    Output("login-error", "children"),
    Input("login-button", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def _handle_login(n_clicks: int | None, email: str | None, password: str | None) -> tuple[Any, str]:
    if not n_clicks:
        return no_update, no_update
    if not email or not password:
        return no_update, "Enter an email and password."
    try:
        session = login(email, password)
    except ApiError as exc:
        return no_update, exc.detail
    data = {
        "base_url": session.base_url,
        "access_token": session.access_token,
        "user": session.user,
    }
    return data, ""


@app.callback(
    Output("session-store", "data", allow_duplicate=True),
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True,
)
def _handle_logout(n_clicks: int | None) -> Any:
    # `prevent_initial_call` only skips the very first app load; a
    # logout-button freshly inserted by _render_page's Output (i.e. every
    # login) still fires this Input once on mount with a falsy n_clicks, so
    # an explicit guard is required or every login immediately logs back out.
    if not n_clicks:
        return no_update
    return None


@app.callback(
    Output("drift-check-status", "children"),
    Input("drift-check-button", "n_clicks"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def _trigger_drift_check(n_clicks: int | None, data: dict[str, Any] | None) -> Any:
    if not n_clicks:
        return no_update
    session = _session_from_store(data)
    if session is None:
        return "Please log in again."
    try:
        post(session, "/drift-reports/check")
    except ApiError as exc:
        return f"Failed to trigger drift check: {exc.detail}"
    return "Drift check scheduled — refresh in a few minutes to see new reports."


if __name__ == "__main__":
    # Dash's default host (127.0.0.1) is loopback-only, unreachable from
    # outside a container -- Docker Compose (docker/docker-compose.yml)
    # sets DASH_HOST=0.0.0.0 and DASH_DEBUG=false for the containerized run.
    app.run(
        host=os.environ.get("DASH_HOST", "127.0.0.1"),
        port=int(os.environ.get("DASH_PORT", "8050")),
        debug=os.environ.get("DASH_DEBUG", "true").lower() == "true",
    )
