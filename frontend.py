import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Sprint Planning Assistant",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI Sprint Planning Assistant")
st.caption("AI-assisted Agile sprint planning, risk analysis and what-if simulation")

# ---------------------------------------------------------
# Load sprint assistant data
# ---------------------------------------------------------

try:
    response = requests.post(
        f"{API_URL}/api/v1/sprint-planning/assistant",
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
except Exception as exc:
    st.error(
        "Unable to connect to FastAPI. "
        "Make sure the backend is running on port 8000."
    )
    st.code(str(exc))
    st.stop()

planning = data["planning"]
risk = data["risk_analysis"]
recommendation = data["recommendation"]
ai = data["ai_analysis"]

# ---------------------------------------------------------
# Sprint overview
# ---------------------------------------------------------

st.header("📊 Sprint Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Average Velocity",
    planning["average_velocity"],
)

col2.metric(
    "Planning Capacity",
    planning["planning_capacity"],
)

col3.metric(
    "Planned Points",
    planning["total_story_points"],
)

col4.metric(
    "Remaining Capacity",
    planning["remaining_capacity"],
)

st.divider()

# ---------------------------------------------------------
# Risk summary
# ---------------------------------------------------------

st.header("⚠️ Sprint Risk")

risk_col1, risk_col2, risk_col3 = st.columns(3)

risk_col1.metric(
    "Overall Risk",
    risk["overall_level"],
)

risk_col2.metric(
    "High Risk Stories",
    risk["high_risk_count"],
)

risk_col3.metric(
    "Medium Risk Stories",
    risk["medium_risk_count"],
)

# ---------------------------------------------------------
# Selected stories
# ---------------------------------------------------------

st.header("📋 Selected Stories")

for story in planning["selected_stories"]:

    story_risk = next(
        (
            r
            for r in risk["story_risks"]
            if r["story_id"] == story["id"]
        ),
        None,
    )

    if story_risk:
        level = story_risk["level"]
        score = story_risk["score"]
        reasons = story_risk["reasons"]
    else:
        level = "UNKNOWN"
        score = 0
        reasons = []

    if level == "HIGH":
        icon = "🔴"
    elif level == "MEDIUM":
        icon = "🟠"
    else:
        icon = "🟢"

    with st.expander(
        f'{icon} {story["id"]} — {story["title"]} '
        f'({story["story_points"]} points)'
    ):
        c1, c2, c3 = st.columns(3)

        c1.write(f'**Priority:** {story["priority"]}')
        c2.write(f'**Risk:** {level}')
        c3.write(f'**Risk Score:** {score}')

        st.write(story["description"])

        if story["dependencies"]:
            st.write(
                "**Dependencies:** "
                + ", ".join(story["dependencies"])
            )

        if story["labels"]:
            st.write(
                "**Labels:** "
                + ", ".join(story["labels"])
            )

        if reasons:
            st.write("**Risk Factors:**")
            for reason in reasons:
                st.write(f"- {reason}")

# ---------------------------------------------------------
# Recommendation
# ---------------------------------------------------------

st.divider()

st.header("🤖 Planning Recommendation")

st.warning(
    recommendation["recommendation"]
)

st.write("### Why?")

for reason in recommendation["rationale"]:
    st.write(f"- {reason}")

col1, col2 = st.columns(2)

with col1:
    st.write("### Preferred Stories")
    for story_id in recommendation["preferred_story_ids"]:
        st.write(f"✅ {story_id}")

with col2:
    st.write("### Avoided Stories")
    for story_id in recommendation["avoided_story_ids"]:
        st.write(f"⚠️ {story_id}")

# ---------------------------------------------------------
# AI analysis
# ---------------------------------------------------------

st.divider()

st.header("🧠 AI Analysis")

st.info(ai["summary"])

st.subheader("AI-Detected Risks")

for item in ai["risks"]:

    story_id = item.get("story_id")
    risk_type = item.get("type", "GENERAL")
    message = item["message"]

    if story_id:
        st.write(
            f"🔴 **{story_id} — {risk_type}**: {message}"
        )
    else:
        label = item.get("label", "")
        st.write(
            f"🟠 **{risk_type} ({label})**: {message}"
        )

st.subheader("AI Recommendations")

for recommendation_item in ai["recommendations"]:
    st.write(f"💡 {recommendation_item}")

# ---------------------------------------------------------
# What-if analysis
# ---------------------------------------------------------

st.divider()

st.header("🔮 What-If Analysis")

story_ids = [
    story["id"]
    for story in planning["selected_stories"]
]

selected_story = st.selectbox(
    "What if we remove this story?",
    story_ids,
)

if st.button(
    "Run What-If Analysis",
    type="primary",
):

    try:
        response = requests.post(
            f"{API_URL}/api/v1/sprint-planning/what-if",
            json={
                "story_id": selected_story,
            },
            timeout=10,
        )

        response.raise_for_status()
        result = response.json()

        st.success(result["explanation"])

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Original Points",
            result["original_points"],
        )

        c2.metric(
            "Simulated Points",
            result["simulated_points"],
        )

        c3.metric(
            "Remaining Capacity",
            result["remaining_capacity"],
        )

        c4.metric(
            "Risk",
            result["simulated_risk"],
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Removed Stories")

            for story_id in result["removed_stories"]:
                st.write(f"❌ {story_id}")

        with col2:
            st.subheader("Added Stories")

            for story_id in result["added_stories"]:
                st.write(f"✅ {story_id}")

        st.subheader("Sprint Comparison")

        st.write(
            f'Original: **{result["original_points"]} points** '
            f'→ Simulated: **{result["simulated_points"]} points**'
        )

        st.write(
            f'Risk: **{result["original_risk"]}** '
            f'→ **{result["simulated_risk"]}**'
        )

    except Exception as exc:
        st.error("What-if analysis failed.")
        st.code(str(exc))

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    "AI Sprint Planning Assistant • "
    "FastAPI + Streamlit • Mock AI Provider"
)
