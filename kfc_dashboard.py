import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

API_URL = "https://api.lunarxr.com/kfc-campaign/unr3s7ric73dl3373ndp0in7"
REFRESH_INTERVAL = 10

st.set_page_config(
    page_title="KFC Campaign Monitor",
    page_icon="🍗",
    layout="wide",
)

st.title("🍗 KFC Campaign — Live Monitor")

if "prev_data" not in st.session_state:
    st.session_state.prev_data = []
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None


@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_data():
    try:
        res = requests.get(API_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        if isinstance(data, list):
            return data, None
        return data.get("data") or data.get("players") or [], None
    except Exception as e:
        return None, str(e)


def check_alerts(prev, current):
    if not prev:
        return
    prev_map = {p["id"]: p for p in prev}
    now = datetime.now().strftime("%H:%M:%S")
    for p in current:
        if p["id"] not in prev_map:
            st.session_state.alerts.insert(
                0, {"type": "new", "msg": f"New player registered: {p['name']} ({p['phone']})", "time": now}
            )
        else:
            old = prev_map[p["id"]]
            if not old["couponCodeRedeemed"] and p["couponCodeRedeemed"]:
                st.session_state.alerts.insert(
                    0, {"type": "redeem", "msg": f"{p['name']} redeemed coupon {p['couponCode']}", "time": now}
                )
            if not old["couponCode"] and p["couponCode"]:
                st.session_state.alerts.insert(
                    0, {"type": "coupon", "msg": f"{p['name']} earned coupon: {p['couponCode']}", "time": now}
                )
    st.session_state.alerts = st.session_state.alerts[:10]


data, error = fetch_data()

if error:
    st.error(f"Failed to fetch data: {error}")
    st.stop()

if data:
    check_alerts(st.session_state.prev_data, data)
    st.session_state.prev_data = data
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

df = pd.DataFrame(data)

# --- Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total registered", len(df))
col2.metric("Played", int((df["highestScore"] > 0).sum()))
col3.metric("Coupons issued", int(df["couponCode"].notna().sum()))
col4.metric("Coupons redeemed", int(df["couponCodeRedeemed"].sum()))

st.caption(f"Last updated: {st.session_state.last_updated} · Auto-refreshes every {REFRESH_INTERVAL}s")

# --- Alerts ---
ALERT_STYLES = {
    "new":    {"bg": "#1a4a1a", "border": "#2d7a2d", "text": "#b6f0b6", "icon": "👤", "label": "NEW PLAYER"},
    "coupon": {"bg": "#1a3a5c", "border": "#2a6098", "text": "#a8d4f5", "icon": "🎟️", "label": "COUPON EARNED"},
    "redeem": {"bg": "#5c3a00", "border": "#c47d00", "text": "#ffe0a0", "icon": "✅", "label": "REDEEMED"},
}

if st.session_state.alerts:
    st.markdown("---")
    st.subheader("🔔 Alerts")
    for a in st.session_state.alerts:
        s = ALERT_STYLES.get(a["type"], ALERT_STYLES["new"])
        st.markdown(
            f'<div style="background:{s["bg"]};border:1px solid {s["border"]};border-radius:8px;'
            f'padding:10px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">'
            f'<span style="font-size:18px">{s["icon"]}</span>'
            f'<div style="flex:1">'
            f'<span style="font-size:11px;font-weight:700;letter-spacing:0.05em;color:{s["border"]}">{s["label"]}</span><br>'
            f'<span style="font-size:14px;color:{s["text"]};font-weight:500">{a["msg"]}</span>'
            f'</div>'
            f'<span style="font-size:12px;color:{s["text"]};opacity:0.7;white-space:nowrap">{a["time"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# --- Leaderboard ---
played_df = df[df["highestScore"] > 0].copy()

if not played_df.empty:
    top_player = played_df.loc[played_df["highestScore"].idxmax()]
    st.markdown("---")
    st.subheader("🏆 Leaderboard")

    st.markdown(
        f'<div style="background:#7c4f00;border:1px solid #c47d00;border-radius:12px;padding:16px 20px;'
        f'margin-bottom:1rem;display:flex;align-items:center;gap:16px;">'
        f'<span style="font-size:36px">🥇</span>'
        f'<div>'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;color:#c47d00">TOP SCORE</div>'
        f'<div style="font-size:22px;font-weight:700;color:#ffffff">{top_player["name"]}</div>'
        f'<div style="font-size:14px;color:#ffe0a0">'
        f'{top_player["phone"]} &nbsp;·&nbsp; '
        f'Score: <strong>{int(top_player["highestScore"])}</strong> &nbsp;·&nbsp; '
        f'Buckets: <strong>{int(top_player["bucketsCompleted"])}</strong> &nbsp;·&nbsp; '
        f'Time: <strong>{top_player["playTime"]}</strong>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    leaderboard = played_df.sort_values("highestScore", ascending=False).reset_index(drop=True)
    leaderboard.index += 1
    MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
    lb_display = leaderboard[["name", "phone", "highestScore", "bucketsCompleted", "playTime"]].copy()
    lb_display.insert(0, "Rank", [MEDALS.get(i, str(i)) for i in leaderboard.index])
    lb_display = lb_display.rename(columns={
        "name": "Name",
        "phone": "Phone",
        "highestScore": "Score",
        "bucketsCompleted": "Buckets",
        "playTime": "Play time",
    })
    st.dataframe(lb_display, use_container_width=True, hide_index=True)

# --- Players table ---
st.markdown("---")
st.subheader("Players")

col_search, col_filter = st.columns([3, 1])
with col_search:
    search = st.text_input("Search by name or phone", placeholder="Type to search…", label_visibility="collapsed")
with col_filter:
    filter_opt = st.selectbox(
        "Filter",
        ["All players", "Played (score > 0)", "Has coupon", "Redeemed", "Coupon not redeemed"],
        label_visibility="collapsed",
    )

filtered = df.copy()

if search:
    mask = (
        filtered["name"].str.contains(search, case=False, na=False)
        | filtered["phone"].astype(str).str.contains(search, na=False)
    )
    filtered = filtered[mask]

if filter_opt == "Played (score > 0)":
    filtered = filtered[filtered["highestScore"] > 0]
elif filter_opt == "Has coupon":
    filtered = filtered[filtered["couponCode"].notna()]
elif filter_opt == "Redeemed":
    filtered = filtered[filtered["couponCodeRedeemed"] == True]
elif filter_opt == "Coupon not redeemed":
    filtered = filtered[filtered["couponCode"].notna() & (filtered["couponCodeRedeemed"] == False)]


def status_label(row):
    if not row["couponCode"]:
        return "No coupon"
    if row["couponCodeRedeemed"]:
        return "✅ Redeemed"
    return "⏳ Pending"


display = filtered[["id", "name", "phone", "highestScore", "playTime", "bucketsCompleted", "couponCode", "couponCodeRedeemed"]].copy()
display["status"] = filtered.apply(status_label, axis=1)
display = display.rename(columns={
    "id": "ID",
    "name": "Name",
    "phone": "Phone",
    "highestScore": "Score",
    "playTime": "Play time",
    "bucketsCompleted": "Buckets",
    "couponCode": "Coupon code",
    "couponCodeRedeemed": "Redeemed",
    "status": "Status",
})
display = display[["ID", "Name", "Phone", "Score", "Play time", "Buckets", "Coupon code", "Status"]]

st.dataframe(display, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(filtered)} of {len(df)} players")

time.sleep(REFRESH_INTERVAL)
st.rerun()