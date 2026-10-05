"""Playwright E2E tests for the Streamlit UI, backed by the local stub.

Covers the three required user flows:
1. record a meal (Add Log)
2. see the macro metrics update
3. see the 7-day trend chart

The database layer behind these flows is covered separately by the
PostgreSQL integration tests.
"""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

LONG = 20_000  # generous timeout: Streamlit renders over a websocket

FOOD_OPTION = re.compile(r"Chicken Breast \(165(\.0)? kcal\/100g\)")


def open_app(page, streamlit_app):
    page.goto(streamlit_app)
    expect(page.locator(".main-header")).to_be_visible(timeout=LONG)
    # products loaded -> the add-food form is rendered
    expect(page.get_by_text("➕ Add Food Log")).to_be_visible(timeout=LONG)


def add_chicken_breast_100g(page):
    page.locator('[data-testid="stSelectbox"]').click()
    page.get_by_role("option", name=FOOD_OPTION).click()
    page.get_by_role("button", name=re.compile("Add Log")).click()


def test_record_meal_and_see_it_in_todays_logs(fresh_stub_data, streamlit_app, page):
    open_app(page, streamlit_app)

    add_chicken_breast_100g(page)

    # the app calls st.rerun() right after st.success(), so the flash message
    # never persists - the durable evidence is the log list and the metrics
    expect(page.get_by_text(re.compile(r"Chicken Breast - 100\.0g")))\
        .to_be_visible(timeout=LONG)
    expect(page.locator('[data-testid="stMetricValue"]').first)\
        .to_have_text("165 kcal", timeout=LONG)


def test_macros_update_after_recording_meal(fresh_stub_data, streamlit_app, page):
    open_app(page, streamlit_app)

    # before the meal everything sits at zero
    expect(page.locator('[data-testid="stMetricValue"]').first)\
        .to_have_text("0 kcal", timeout=LONG)

    add_chicken_breast_100g(page)

    # 100g Chicken Breast: 165 kcal, 31g protein, 0g carbs, 3.6g fat
    metrics = page.locator('[data-testid="stMetricValue"]')
    expect(metrics.nth(0)).to_have_text("165 kcal", timeout=LONG)
    expect(metrics.nth(1)).to_have_text("31.0 g", timeout=LONG)
    expect(metrics.nth(2)).to_have_text("0.0 g", timeout=LONG)
    expect(metrics.nth(3)).to_have_text("3.6 g", timeout=LONG)


def test_weekly_trend_chart_renders_with_data(fresh_stub_data, streamlit_app, page):
    open_app(page, streamlit_app)

    add_chicken_breast_100g(page)

    expect(page.get_by_text("📈 Past 7 Days Trend")).to_be_visible(timeout=LONG)

    # calorie trend chart: goal reference line + today's tick label
    chart = page.locator(".js-plotly-plot").first
    expect(chart).to_be_visible(timeout=LONG)
    expect(chart.get_by_text("Goal: 2500 kcal")).to_be_visible(timeout=LONG)
    expect(chart.get_by_text("10/05")).to_be_visible(timeout=LONG)
