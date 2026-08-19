"""HR and Manager dashboards (Module 11). Everything renders from the
backend REST API (Modules 4-11) via dashboards/common/api_client.py — no
direct database access.

    PYTHONPATH=dashboards poetry run streamlit run dashboards/streamlit_app/app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from common.api_client import ApiError, ApiSession, get, login
from common.colors import RISK_LEVEL_COLORS, RISK_LEVEL_ORDER, SEQUENTIAL_BLUE

st.set_page_config(page_title="Retention Platform", page_icon=":bar_chart:", layout="wide")


def _login_screen() -> None:
    st.title("AI Employee Retention Platform")
    st.caption("HR and Manager dashboards")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        try:
            st.session_state.api_session = login(email, password)
        except ApiError as exc:
            st.error(exc.detail)
        else:
            st.rerun()


def _logout_button(session: ApiSession) -> None:
    with st.sidebar:
        st.write(f"**{session.user.get('email')}**")
        st.write(", ".join(session.roles) or "no roles")
        if st.button("Log out"):
            del st.session_state["api_session"]
            st.rerun()


def _risk_bar_chart(distribution: dict[str, int], *, title: str) -> None:
    df = pd.DataFrame(
        {
            "risk_level": RISK_LEVEL_ORDER,
            "employees": [distribution.get(level, 0) for level in RISK_LEVEL_ORDER],
        }
    )
    fig = px.bar(
        df,
        x="risk_level",
        y="employees",
        color="risk_level",
        color_discrete_map=RISK_LEVEL_COLORS,
        category_orders={"risk_level": RISK_LEVEL_ORDER},
        title=title,
    )
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Employees")
    st.plotly_chart(fig, use_container_width=True)


def _risk_summary_table(
    session: ApiSession, *, department_id: int | None, manager_id: int | None
) -> None:
    page = get(
        session,
        "/reports/attrition-risk-summary",
        department_id=department_id,
        manager_id=manager_id,
        limit=50,
    )
    items = page["items"]
    if not items:
        st.info("No attrition predictions on record yet for this scope.")
        return
    columns = [
        "employee_number",
        "first_name",
        "last_name",
        "department_name",
        "risk_level",
        "risk_score",
    ]
    df = pd.DataFrame(items)[columns]
    st.dataframe(df, hide_index=True, use_container_width=True)


def _hr_view(session: ApiSession) -> None:
    st.header("HR Dashboard")

    kpis = get(session, "/reports/department-kpis")
    if not kpis:
        st.info("No departments on record yet — run the ETL pipeline (ml.etl.pipeline).")
        return
    kpi_df = pd.DataFrame(kpis)

    total_headcount = int(kpi_df["active_headcount"].sum())
    total_terminations = int(kpi_df["terminations_last_12_months"].sum())
    company_turnover = round(total_terminations / max(total_headcount, 1) * 100, 2)

    col1, col2, col3 = st.columns(3)
    col1.metric("Active headcount", f"{total_headcount:,}")
    col2.metric("Terminations (12mo)", f"{total_terminations:,}")
    col3.metric("Company-wide turnover", f"{company_turnover}%")

    st.subheader("Department KPIs")
    st.dataframe(
        kpi_df.rename(
            columns={
                "department_name": "Department",
                "active_headcount": "Headcount",
                "terminations_last_12_months": "Terminations (12mo)",
                "avg_current_salary": "Avg salary",
                "avg_tenure_years": "Avg tenure (yrs)",
                "turnover_rate_12mo": "Turnover rate (12mo)",
            }
        ).drop(columns=["department_id"]),
        hide_index=True,
        use_container_width=True,
    )

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            kpi_df,
            x="department_name",
            y="active_headcount",
            title="Headcount by department",
            color_discrete_sequence=[SEQUENTIAL_BLUE],
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Employees")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        distribution = get(session, "/reports/risk-distribution")
        _risk_bar_chart(distribution, title="Attrition risk distribution")

    st.subheader("Employees at risk")
    department_options = {"All departments": None} | {
        row["department_name"]: row["department_id"] for row in kpis
    }
    selected = st.selectbox("Department", options=list(department_options))
    _risk_summary_table(session, department_id=department_options[selected], manager_id=None)


def _manager_view(session: ApiSession) -> None:
    st.header("Manager Dashboard")

    if session.employee_id is None:
        st.warning("Your account isn't linked to an employee record, so no team can be shown.")
        return

    team = get(session, "/employees", manager_id=session.employee_id, limit=100)
    if team["total"] == 0:
        st.info("No one currently reports to you.")
        return

    st.metric("Direct reports", team["total"])
    columns = ["employee_number", "first_name", "last_name", "job_title"]
    team_df = pd.DataFrame(team["items"])[columns]
    st.subheader("My team")
    st.dataframe(team_df, hide_index=True, use_container_width=True)

    st.subheader("Attrition risk for my team")
    _risk_summary_table(session, department_id=None, manager_id=session.employee_id)


_VIEWS = {"hr": ("HR", _hr_view), "admin": ("HR", _hr_view), "manager": ("Manager", _manager_view)}


def _main_screen(session: ApiSession) -> None:
    _logout_button(session)

    available = {label: view for role, (label, view) in _VIEWS.items() if session.has_role(role)}
    if not available:
        st.info("Your role doesn't have a dashboard view yet (HR, admin or manager only).")
        return

    if len(available) == 1:
        next(iter(available.values()))(session)
        return

    tabs = st.tabs(list(available))
    for tab, view in zip(tabs, available.values(), strict=True):
        with tab:
            view(session)


def main() -> None:
    if st.session_state.get("api_session") is None:
        _login_screen()
    else:
        _main_screen(st.session_state.api_session)


main()
