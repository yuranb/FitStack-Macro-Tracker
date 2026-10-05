"""
FitStack Macro Tracker - Nutrition Tracking Application
Tech Stack: Streamlit + Supabase (PostgreSQL)

Data access lives in database.py (framework-agnostic functions that take a
client); nutrition math and aggregation live in nutrition.py. This module is
only Streamlit: caching, error display and UI.
"""

import os
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import (
    DEFAULT_GOALS,
    add_food_log,
    delete_log,
    fetch_foods,
    fetch_goals,
    fetch_todays_logs,
    fetch_week_logs,
    update_goals,
)
from nutrition import (
    build_weekly_trend,
    calc_nutrition,
    daily_totals,
    goal_progress,
)

# Config constants - makes it easy to adjust later
PRODUCT_CACHE_TIME = 300  # 5 min should be enough since products rarely change
GOAL_CACHE_TIME = 60
SHOW_LAST_DAYS = 7
DEFAULT_QTY = 100.0

# ============================================
# Database Connection
# ============================================
def _supabase_config() -> tuple[str, str]:
    """Env vars win so tests/E2E can run without touching secrets.toml."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        return url, key
    return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase() -> Client:
    """Connect to Supabase - using cache_resource so connection persists"""
    try:
        url, key = _supabase_config()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {str(e)}")
        st.stop()

supabase = init_supabase()

# ============================================
# Data fetching with Cache-Aside strategy
# ============================================
# Cache-Aside pattern: check cache first, if miss then query database
# This reduces database load significantly for read-heavy operations
# Products and goals change infrequently so caching makes sense

@st.cache_data(ttl=PRODUCT_CACHE_TIME)
def get_foods() -> pd.DataFrame:
    try:
        return pd.DataFrame(fetch_foods(supabase))
    except Exception as e:
        st.error(f"Failed to fetch product data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=GOAL_CACHE_TIME)
def get_goals() -> dict:
    try:
        return fetch_goals(supabase)
    except Exception as e:
        st.warning(f"Failed to fetch goals, using defaults: {str(e)}")
        return dict(DEFAULT_GOALS)

def get_todays_logs(date: str) -> pd.DataFrame:
    """Not cached because logs change frequently throughout the day"""
    try:
        return pd.DataFrame(fetch_todays_logs(supabase, date))
    except Exception as e:
        st.error(f"Failed to fetch daily logs: {str(e)}")
        return pd.DataFrame()

def get_week_data() -> pd.DataFrame:
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=SHOW_LAST_DAYS - 1)
        return pd.DataFrame(fetch_week_logs(supabase, start_date, end_date))
    except Exception as e:
        st.error(f"Failed to fetch weekly summary: {str(e)}")
        return pd.DataFrame()

# ============================================
# Streamlit UI
# ============================================
st.set_page_config(
    page_title="FitStack Macro Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">💪 FitStack Macro Tracker</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Settings")

    selected_date = st.date_input(
        "📅 Select Date",
        value=datetime.now().date(),
        max_value=datetime.now().date()
    )

    st.divider()

    st.subheader("🎯 Daily Goals")
    user_goals = get_goals()

    with st.expander("Modify Goals", expanded=False):
        new_cals = st.number_input("Calories (kcal)", value=user_goals["daily_calories"], min_value=1000, max_value=5000, step=100)
        new_protein = st.number_input("Protein (g)", value=user_goals["daily_protein"], min_value=50, max_value=300, step=10)
        new_carbs = st.number_input("Carbs (g)", value=user_goals["daily_carbs"], min_value=50, max_value=500, step=10)
        new_fat = st.number_input("Fat (g)", value=user_goals["daily_fat"], min_value=20, max_value=200, step=5)

        if st.button("💾 Save Goals", use_container_width=True):
            try:
                update_goals(supabase, new_cals, new_protein, new_carbs, new_fat)
            except Exception as e:
                st.error(f"Failed to update goals: {str(e)}")
            else:
                get_goals.clear()  # clear cache so new goals show up immediately
                st.success("Goals updated successfully!")
                st.rerun()

    st.divider()

    # Cache info - mainly for debugging
    st.caption("💡 Cache Strategy: Cache-Aside")
    st.caption(f"Product data TTL: {PRODUCT_CACHE_TIME}s")
    if st.button("🔄 Refresh Cache", use_container_width=True):
        get_foods.clear()
        get_goals.clear()
        st.success("Cache cleared!")
        st.rerun()

date_str = selected_date.isoformat()
todays_logs = get_todays_logs(date_str)
todays_totals = daily_totals(todays_logs)

# ============================================
# Main dashboard
# ============================================
st.subheader(f"📊 Nutrition Intake - {selected_date.strftime('%Y-%m-%d')}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Progress bars cap at 100% or they break
    cal_pct = goal_progress(todays_totals["calories"], user_goals["daily_calories"])
    st.metric("🔥 Calories", f"{todays_totals['calories']:.0f} kcal", f"Goal: {user_goals['daily_calories']} kcal")
    st.progress(cal_pct / 100)

with col2:
    pro_pct = goal_progress(todays_totals["protein"], user_goals["daily_protein"])
    st.metric("🥩 Protein", f"{todays_totals['protein']:.1f} g", f"Goal: {user_goals['daily_protein']} g")
    st.progress(pro_pct / 100)

with col3:
    carb_pct = goal_progress(todays_totals["carbs"], user_goals["daily_carbs"])
    st.metric("🍚 Carbs", f"{todays_totals['carbs']:.1f} g", f"Goal: {user_goals['daily_carbs']} g")
    st.progress(carb_pct / 100)

with col4:
    fat_pct = goal_progress(todays_totals["fat"], user_goals["daily_fat"])
    st.metric("🥑 Fat", f"{todays_totals['fat']:.1f} g", f"Goal: {user_goals['daily_fat']} g")
    st.progress(fat_pct / 100)

st.divider()

# ============================================
# Food logging
# ============================================
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("➕ Add Food Log")

    foods_df = get_foods()

    if not foods_df.empty:
        food_options = {row["name"]: row for _, row in foods_df.iterrows()}
        selected_food = st.selectbox(
            "Select Food",
            options=list(food_options.keys()),
            format_func=lambda x: f"{x} ({food_options[x]['calories']} kcal/100{food_options[x]['serving_unit']})"
        )

        food_data = food_options[selected_food]

        amount = st.number_input(
            f"Serving Size ({food_data['serving_unit']})",
            min_value=1.0,
            max_value=1000.0,
            value=DEFAULT_QTY,
            step=10.0
        )

        # Show preview before adding
        nutri_preview = calc_nutrition(food_data, amount)
        st.info(f"""
        **Estimated Intake:**
        - 🔥 Calories: {nutri_preview['calories']:.1f} kcal
        - 🥩 Protein: {nutri_preview['protein']:.1f} g
        - 🍚 Carbs: {nutri_preview['carbs']:.1f} g
        - 🥑 Fat: {nutri_preview['fat']:.1f} g
        """)

        if st.button("✅ Add Log", type="primary", use_container_width=True):
            try:
                add_food_log(supabase, int(food_data["id"]), amount, date_str)
            except Exception as e:
                st.error(f"Failed to add food log: {str(e)}")
            else:
                st.success(f"Added: {selected_food} {amount}{food_data['serving_unit']}")
                st.rerun()
    else:
        st.warning("No food data available. Please add products to the database first.")

with col_right:
    st.subheader("📋 Today's Logs")

    if not todays_logs.empty:
        for _, log in todays_logs.iterrows():
            food = log.get("products", {})
            if food:
                nutri_vals = calc_nutrition(food, log["quantity"])

                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(f"**{food.get('name', 'Unknown')}** - {log['quantity']}{food.get('serving_unit', 'g')}")
                    st.caption(f"🔥 {nutri_vals['calories']:.0f} kcal | 🥩 {nutri_vals['protein']:.1f}g | 🍚 {nutri_vals['carbs']:.1f}g | 🥑 {nutri_vals['fat']:.1f}g")
                with col_b:
                    # Each button needs unique key or Streamlit complains
                    if st.button("🗑️", key=f"del_{log['id']}", help="Delete this log"):
                        try:
                            delete_log(supabase, log["id"])
                        except Exception as e:
                            st.error(f"Failed to delete food log: {str(e)}")
                        else:
                            st.rerun()
                st.divider()
    else:
        st.info("No logs for today yet. Add your first meal!")

# ============================================
# Charts
# ============================================
st.divider()
st.subheader(f"📈 Past {SHOW_LAST_DAYS} Days Trend")

week_data = get_week_data()

if not week_data.empty:
    # Aggregate nutrition by day, oldest first, zero-filled for missing days
    summary_df = build_weekly_trend(week_data, datetime.now().date(), SHOW_LAST_DAYS)

    tab1, tab2 = st.tabs(["📊 Calorie Trend", "📈 Macronutrients"])

    with tab1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=summary_df["date"],
            y=summary_df["calories"],
            name="Actual Intake",
            marker_color="#667eea"
        ))

        # Add goal reference line
        fig.add_hline(
            y=user_goals["daily_calories"],
            line_dash="dash",
            line_color="red",
            annotation_text=f"Goal: {user_goals['daily_calories']} kcal"
        )

        fig.update_layout(
            title="Daily Calorie Intake",
            xaxis_title="Date",
            yaxis_title="Calories (kcal)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=summary_df["date"],
            y=summary_df["protein"],
            name="Protein (g)",
            mode="lines+markers",
            line=dict(color="#e74c3c")
        ))

        fig2.add_trace(go.Scatter(
            x=summary_df["date"],
            y=summary_df["carbs"],
            name="Carbs (g)",
            mode="lines+markers",
            line=dict(color="#3498db")
        ))

        fig2.add_trace(go.Scatter(
            x=summary_df["date"],
            y=summary_df["fat"],
            name="Fat (g)",
            mode="lines+markers",
            line=dict(color="#f39c12")
        ))

        fig2.update_layout(
            title="Macronutrient Trends",
            xaxis_title="Date",
            yaxis_title="Grams (g)",
            height=400
        )

        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No historical data yet. Start tracking your meals!")

st.divider()
st.caption("💪 FitStack Macro Tracker | Data stored in Supabase (PostgreSQL) | Using Cache-Aside strategy")
