# ott_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ------------------ Step 1: Page Config ------------------
st.set_page_config(page_title="OTT Analytics Dashboard", layout="wide")

# ------------------ Step 2: Load Data ------------------
@st.cache_data
def load_data():
    return pd.read_excel("Clickstream Assignment.xlsx", sheet_name="Clickstream Data")

df = load_data()
df_copy = df.copy()

# ------------------ Step 3: Prepare Data ------------------
df_copy["event_time"] = pd.to_datetime(df_copy["event_time"])
df_copy["event_date"] = df_copy["event_time"].dt.date

funnel_steps = [
    "SUBSCRIPTION-CURATED-PLAN-SELECTION-LAUNCH",
    "SUBSCRIPTION-CURATED-PLAN-SELECTION-PROCEED",
    "APP-SELECTION-PAGE",
    "CHOOSE_YOUR_APP_PROCEED",
    "SUBSCRIPTION-SUMMARY-LAUNCH",
    "SUBSCRIPTION-SUMMARY-PROCEED",
    "PAYMENT-INITIATE",
    "PAYMENT",
    "BINGE-SUBSCRIPTION",
    "SUBSCRIBE-SUCCESS",
]

# ------------------ Step 4: Helper Functions ------------------
def create_sankey_data(filtered_df):
    sankey_list = []
    for i in range(len(funnel_steps) - 1):
        source = funnel_steps[i]
        target = funnel_steps[i + 1]
        src_count = filtered_df[filtered_df["event_name"] == source].shape[0]
        tgt_count = filtered_df[filtered_df["event_name"] == target].shape[0]
        conv_percent = (tgt_count / src_count * 100) if src_count > 0 else 0
        sankey_list.append({
            "source": source,
            "target": target,
            "value": min(src_count, tgt_count),
            "percent": conv_percent
        })
    return sankey_list


def plot_vertical_sankey(filtered_df):
    sankey_data = create_sankey_data(filtered_df)
    labels = funnel_steps
    source_idx = [labels.index(x["source"]) for x in sankey_data]
    target_idx = [labels.index(x["target"]) for x in sankey_data]
    values = [x["value"] for x in sankey_data]
    percentages = [x["percent"] for x in sankey_data]

    node_colors = px.colors.qualitative.Pastel
    node_color_map = [node_colors[i % len(node_colors)] for i in range(len(labels))]
    link_colors = [node_color_map[src] for src in source_idx]

    # Create Sankey figure
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                orientation="v",  # 🔥 Vertical layout
                node=dict(
                    pad=30,
                    thickness=30,
                    line=dict(color="black", width=1),
                    label=labels,
                    color=node_color_map,
                ),
                link=dict(
                    source=source_idx,
                    target=target_idx,
                    value=values,
                    color=link_colors,
                    hovertemplate=(
                        "From %{source.label}<br>"
                        "To %{target.label}<br>"
                        "<b>%{value}</b> users<br>"
                        "Conversion: <b>%{customdata:.1f}%</b><extra></extra>"
                    ),
                    customdata=percentages,
                ),
            )
        ]
    )

    fig.update_layout(
        title="🎯 Funnel Conversion (Top to Bottom Flow)",
        font_size=12,
        height=700,
    )
    return fig

# ------------------ Step 5: Layout Filters ------------------
st.title("🎬 OTT Subscription & Device Dashboard")

col1, col2, col3 = st.columns(3)
with col1:
    start_date = st.date_input("📅 Start Date", df_copy["event_date"].min())
with col2:
    end_date = st.date_input("📅 End Date", df_copy["event_date"].max())
with col3:
    platform = st.selectbox("🖥 Platform", ["All"] + sorted(df_copy["platform"].dropna().unique().tolist()))

user_type = st.selectbox("👤 User Type", ["All"] + sorted(df_copy["user_type"].dropna().unique().tolist()))

# Filter data
filtered_df = df_copy[
    (df_copy["event_date"] >= start_date) & (df_copy["event_date"] <= end_date)
]
if platform != "All":
    filtered_df = filtered_df[filtered_df["platform"] == platform]
if user_type != "All":
    filtered_df = filtered_df[filtered_df["user_type"] == user_type]

# ------------------ Step 6: Visualizations ------------------

## 🔹 Funnel Bar
st.subheader("📈 Subscription Funnel Overview")
funnel_df = filtered_df[filtered_df["event_name"].isin(funnel_steps)]
funnel_counts = (
    funnel_df["event_name"].value_counts().reindex(funnel_steps).reset_index()
)
funnel_counts.columns = ["event_name", "count"]
funnel_fig = px.bar(
    funnel_counts,
    x="event_name",
    y="count",
    text="count",
    color="count",
    color_continuous_scale="Blues",
)
funnel_fig.update_traces(textposition="outside")
st.plotly_chart(funnel_fig, use_container_width=True)

## 🔹 Vertical Sankey
st.subheader("🔻 Funnel Conversion Flow (Vertical Sankey)")
sankey_fig = plot_vertical_sankey(filtered_df)
st.plotly_chart(sankey_fig, use_container_width=True)

## 🔹 Daily Trends
st.subheader("📅 Daily Event Trends")
daily_events = filtered_df.groupby("event_date").size().reset_index(name="event_count")
daily_fig = px.line(
    daily_events,
    x="event_date",
    y="event_count",
    markers=True,
    labels={"event_date": "Date", "event_count": "Event Count"},
)
st.plotly_chart(daily_fig, use_container_width=True)

## 🔹 Campaign Conversions
st.subheader("🎯 Campaign Conversions")
campaign_conv = filtered_df[
    filtered_df["event_name"].isin(["BINGE-SUBSCRIPTION", "SUBSCRIBE-SUCCESS"])
]
campaign_summary = (
    campaign_conv.groupby("af_campaign").size().reset_index(name="conversions")
)
campaign_fig = px.bar(
    campaign_summary.sort_values("conversions", ascending=False),
    x="af_campaign",
    y="conversions",
    color="conversions",
    color_continuous_scale="Viridis",
)
st.plotly_chart(campaign_fig, use_container_width=True)

## 🔹 Device / OS
st.subheader("📱 Device / OS Distribution")
device_summary = filtered_df["mp_os"].value_counts().reset_index()
device_summary.columns = ["mp_os", "count"]
device_fig = px.pie(device_summary, values="count", names="mp_os", title="OS Distribution")
st.plotly_chart(device_fig, use_container_width=True)

## 🔹 Payment Method / Status
st.subheader("💳 Payment Method & Status")
if "payment_method" in filtered_df.columns and "payment_status" in filtered_df.columns:
    payment_summary = (
        filtered_df.groupby(["payment_method", "payment_status"])
        .size()
        .reset_index(name="count")
    )
    payment_fig = px.sunburst(
        payment_summary,
        path=["payment_method", "payment_status"],
        values="count",
        title="Payment Method & Status Breakdown",
    )
    st.plotly_chart(payment_fig, use_container_width=True)

## 🔹 Subscription Pack Popularity
if "pack_name" in filtered_df.columns:
    st.subheader("🎁 Subscription Pack Popularity")
    pack_summary = (
        filtered_df.groupby("pack_name")["pack_price"].agg(["count", "mean"]).reset_index()
    )
    pack_fig = px.bar(
        pack_summary.sort_values("count", ascending=False),
        x="pack_name",
        y="count",
        title="Subscription Pack Popularity",
    )
    st.plotly_chart(pack_fig, use_container_width=True)

# ------------------ Step 7: Device Attribute Explorer ------------------
st.sidebar.header("📊 Explore Device Attributes")
columns_to_visualize = [
    "mp_brand", "mp_browser", "mp_carrier", "mp_city", "mp_country_code",
    "mp_manufacturer", "mp_model", "mp_os", "mp_os_version", "mp_region", "mp_wifi"
]
columns_to_visualize = [c for c in columns_to_visualize if c in df_copy.columns]
selected_col = st.sidebar.selectbox("Select Column", columns_to_visualize)
top_n = st.sidebar.slider("Top N values", 5, 50, 20)

st.subheader(f"📶 Distribution of **{selected_col}**")
col_counts = df_copy[selected_col].value_counts().nlargest(top_n).reset_index()
col_counts.columns = [selected_col, "Count"]

dist_fig = px.bar(
    col_counts,
    x=selected_col,
    y="Count",
    text="Count",
    color="Count",
    color_continuous_scale="Viridis",
)
dist_fig.update_traces(textposition="outside")
st.plotly_chart(dist_fig, use_container_width=True)
with st.expander(f"Show Top {top_n} {selected_col} Values"):
    st.dataframe(col_counts)
