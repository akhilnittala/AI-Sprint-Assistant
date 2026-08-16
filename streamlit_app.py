import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/api/v1/sprint-planning"

def api_post(path, payload):
    if path.startswith("/intelligence"):
        url = f"http://127.0.0.1:8000/api/v1{path}"
    else:
        url = f"{API_URL}{path}"

    response = requests.post(
        url,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

st.set_page_config(
    page_title="AI Sprint Planning Assistant",
    page_icon="🤖",
    layout="wide",
)

if "similarity_results" not in st.session_state:
    st.session_state.similarity_results = {}

st.title("🤖 AI Sprint Planning Assistant")
st.caption("Real-time sprint planning using Jira backlog data")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def api_get(path):
    response = requests.get(
        f"{API_URL}{path}",
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.header("Jira")

    if st.button(
        "🔄 Refresh Jira Backlog",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.header("⚙️ Team Sprint Configuration")

    st.caption(
        "Configure sprint capacity independently for each team."
    )

    team_configs = {}

    default_configs = {
        "Tangerine": {
            "developers": 3,
            "qa_engineers": 1,
            "capacity_per_person": 8,
            "velocity": 28,
        },
        "Crimson": {
            "developers": 3,
            "qa_engineers": 1,
            "capacity_per_person": 8,
            "velocity": 24,
        },
        "Scarlet": {
            "developers": 2,
            "qa_engineers": 1,
            "capacity_per_person": 8,
            "velocity": 18,
        },
    }

    for team_name, defaults in default_configs.items():

        with st.expander(
            f"👥 {team_name}",
            expanded=True,
        ):

            developers = st.number_input(
                "Developers",
                min_value=0,
                max_value=100,
                value=defaults["developers"],
                step=1,
                key=f"{team_name}_developers",
            )

            qa_engineers = st.number_input(
                "QA Engineers",
                min_value=0,
                max_value=100,
                value=defaults["qa_engineers"],
                step=1,
                key=f"{team_name}_qa",
            )

            capacity_per_person = st.number_input(
                "Capacity per person",
                min_value=1,
                max_value=50,
                value=defaults["capacity_per_person"],
                step=1,
                key=f"{team_name}_capacity",
            )

            velocity = st.number_input(
                "Historical velocity",
                min_value=0,
                max_value=500,
                value=defaults["velocity"],
                step=1,
                key=f"{team_name}_velocity",
            )

            people = developers + qa_engineers

            staffing_capacity = (
                people * capacity_per_person
            )

            planning_capacity = (
                min(
                    staffing_capacity,
                    velocity,
                )
                if velocity > 0
                else staffing_capacity
            )

            st.metric(
                "Planning Capacity",
                f"{planning_capacity} pts",
            )

            team_configs[team_name] = {
                "developers": developers,
                "qa_engineers": qa_engineers,
                "people": people,
                "capacity_per_person": capacity_per_person,
                "velocity": velocity,
                "staffing_capacity": staffing_capacity,
                "planning_capacity": planning_capacity,
            }

    st.info(
        "Planning capacity = min("
        "people × capacity/person, velocity)"
    )


# ---------------------------------------------------------
# Load backlog
# ---------------------------------------------------------

try:
    backlog = api_get("/backlog")
    stories = backlog.get("stories", [])
except Exception as e:
    st.error(f"Unable to connect to backend: {e}")
    st.stop()


# ---------------------------------------------------------
# Jira information
# ---------------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric(
    "Jira Backlog",
    f"{len(stories)} stories",
)

todo_count = sum(
    1
    for story in stories
    if story.get("status") == "TODO"
)

col2.metric(
    "Ready for Planning",
    todo_count,
)

total_points = sum(
    story.get("story_points", 0)
    for story in stories
)

col3.metric(
    "Available Points",
    total_points,
)


# ---------------------------------------------------------
# Team Planning
# ---------------------------------------------------------

st.divider()

st.header("🧠 AI Sprint Planning Intelligence")

st.write(
    "Generate sprint plans independently for each team "
    "based on Jira backlog stories and team capacity."
)


if st.button(
    "🚀 Analyze & Generate Sprint Plans",
    type="primary",
    use_container_width=True,
):
    with st.spinner(
        "Analyzing Jira stories by team..."
    ):
        try:
            planning_config = {
                "teams": team_configs
            }

            response = requests.post(
                f"{API_URL}/team-plan",
                json=planning_config,
                timeout=120,
            )

            response.raise_for_status()

            st.session_state.team_plan = response.json()

        except requests.RequestException as e:
            st.error(f"Unable to generate team sprint plans: {e}")


# =========================================================
# SPRINT REVIEW
# =========================================================

st.divider()

with st.expander(
    "🔎 Sprint Review",
    expanded=False,
):

    st.write(
        "Generate a sprint review from Jira using the "
        "selected active sprint, assignees, statuses, "
        "story points and latest comments."
    )

    try:
        sprint_response = requests.get(
            f"{API_URL}/active-sprints",
            timeout=30,
        )

        sprint_response.raise_for_status()

        active_sprints = sprint_response.json().get(
            "sprints",
            [],
        )

    except Exception as e:
        active_sprints = []
        st.error(
            f"Unable to load active sprints: {e}"
        )

    if not active_sprints:

        st.info(
            "No active Jira sprints are available."
        )

    else:

        sprint_options = {
            (
                f"{sprint['name']} "
                f"(#{sprint['id']})"
            ): sprint["id"]
            for sprint in active_sprints
        }

        selected_sprint_name = st.selectbox(
            "Select current sprint",
            list(sprint_options.keys()),
            key="sprint_review_selector",
        )

        selected_sprint_id = sprint_options[
            selected_sprint_name
        ]

        if st.button(
            "📋 Generate Sprint Review",
            type="primary",
            use_container_width=True,
            key="generate_sprint_review",
        ):

            with st.spinner(
                "Loading Jira sprint issues and comments..."
            ):

                try:
                    review_response = requests.get(
                        f"{API_URL}/sprint-review/"
                        f"{selected_sprint_id}",
                        timeout=180,
                    )

                    review_response.raise_for_status()

                    st.session_state.sprint_review = (
                        review_response.json()
                    )

                except Exception as e:
                    st.error(
                        f"Sprint review generation failed: {e}"
                    )

        report = st.session_state.get(
            "sprint_review"
        )

        if report:

            sprint = report["sprint"]
            summary = report["summary"]

            st.subheader(
                f"📊 {sprint['name']}"
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Total",
                summary["total"],
            )

            c2.metric(
                "Closed",
                summary["closed"],
            )

            c3.metric(
                "In Progress",
                summary["in_progress"],
            )

            c4.metric(
                "In Review",
                summary["review"],
            )

            c5.metric(
                "Other",
                summary["other"],
            )

            def render_review_section(
                title,
                items,
            ):

                st.markdown(
                    f"### {title}"
                )

                if not items:
                    st.info(
                        "No stories in this category."
                    )
                    return

                for item in items:

                    st.markdown(
                        f"**{item['key']} — "
                        f"{item['title']}**"
                    )

                    a, b, c = st.columns(3)

                    a.write(
                        f"👤 {item['assignee']}"
                    )

                    b.write(
                        f"📌 Jira: {item['status']}"
                    )

                    c.write(
                        f"🤖 Comment: "
                        f"{item['comment_status']}"
                    )

                    st.caption(
                        f"Story points: "
                        f"{item['story_points']}"
                    )


                    # -----------------------------------------
                    # Pull Requests for IN REVIEW Jira
                    # -----------------------------------------
                    item_status = item.get("status", "")

                    if isinstance(item_status, dict):
                        item_status = item_status.get("name", "")

                    normalized_status = (
                        str(item_status)
                        .upper()
                        .replace("_", "")
                        .replace("-", "")
                        .replace(" ", "")
                    )

                    if normalized_status in {
                        "INREVIEW",
                        "REVIEW",
                        "CODEREVIEW",
                        "CODEVIEW",
                    }:
                        pull_requests = item.get(
                            "pull_requests",
                            [],
                        )

                        with st.expander(
                            f"🔀 Pull Requests ({len(pull_requests)})",
                            expanded=bool(pull_requests),
                        ):
                            if pull_requests:
                                for pr in pull_requests:
                                    title = pr.get(
                                        "title",
                                        "Git Pull Request",
                                    )

                                    url = pr.get("url")
                                    author = pr.get("author")
                                    status = pr.get(
                                        "status",
                                        "Linked",
                                    )
                                    repository = pr.get(
                                        "repository"
                                    )

                                    st.markdown(
                                        f"**{title}**"
                                    )

                                    details = []

                                    if repository:
                                        details.append(
                                            f"📦 {repository}"
                                        )

                                    if author:
                                        details.append(
                                            f"👤 {author}"
                                        )

                                    if status:
                                        details.append(
                                            f"🔄 {status}"
                                        )

                                    if details:
                                        st.caption(
                                            " • ".join(details)
                                        )

                                    if url:
                                        st.link_button(
                                            "View Pull Request →",
                                            url,
                                        )

                                    st.divider()
                            else:
                                st.info(
                                    "No pull request linked to this Jira issue."
                                )

                    if item["latest_comment"]:
                        st.info(
                            "Latest comment: "
                            + item["latest_comment"]
                        )

                    st.divider()

            render_review_section(
                "✅ Completed / Closed",
                report["closed"],
            )

            render_review_section(
                "🔄 In Progress",
                report["in_progress"],
            )

            render_review_section(
                "👀 In Review",
                report["review"],
            )

            render_review_section(
                "📋 Other Sprint Items",
                report["other"],
            )

            markdown = (
                requests.get(
                    f"{API_URL}/sprint-review/"
                    f"{selected_sprint_id}/markdown",
                    timeout=180,
                )
                .json()
                .get("content", "")
            )

            st.download_button(
                "📄 Download Sprint Review",
                data=markdown,
                file_name=(
                    sprint["name"]
                    .replace(" ", "_")
                    .replace("/", "_")
                    + ".md"
                ),
                mime="text/markdown",
                use_container_width=True,
            )


# =========================================================
# BACKLOG INTELLIGENCE
# Analyze the COMPLETE Jira backlog for duplicates/similarity
# =========================================================

st.divider()

with st.expander("🧠 Backlog Intelligence", expanded=False):

    backlog_stories = backlog.get("stories", []) if isinstance(backlog, dict) else []

    if not backlog_stories:
        st.info("No Jira backlog stories available for analysis.")
    elif len(backlog_stories) < 2:
        st.info("At least two backlog stories are required.")
    else:

        if st.button(
            "🔍 Analyze Entire Backlog for Duplicates",
            key="analyze_backlog_duplicates",
            use_container_width=True,
        ):

            with st.spinner(
                f"Analyzing {len(backlog_stories)} Jira stories for "
                "duplicates and similarities..."
            ):
                try:
                    result = api_post(
                        "/intelligence/stories/similar",
                        {"stories": backlog_stories},
                    )

                    st.session_state.backlog_similarity = result

                except Exception as e:
                    st.error(
                        f"Backlog duplicate analysis failed: {e}"
                    )

        result = st.session_state.get(
            "backlog_similarity"
        )

        if result:

            results = result.get(
                "results",
                result.get("stories", []),
            )

            likely_duplicates = []
            highly_similar = []
            related = []

            seen_pairs = set()

            for item in results:

                source_id = item.get("story_id")
                source_title = item.get("title", "")

                for similar in item.get(
                    "similar_stories",
                    [],
                ):

                    target_id = similar.get("story_id")

                    if not source_id or not target_id:
                        continue

                    pair = tuple(
                        sorted(
                            [
                                str(source_id),
                                str(target_id),
                            ]
                        )
                    )

                    if pair in seen_pairs:
                        continue

                    seen_pairs.add(pair)

                    classification = similar.get(
                        "classification",
                        "RELATED",
                    )

                    entry = {
                        "source_id": source_id,
                        "source_title": source_title,
                        "target_id": target_id,
                        "target_title": similar.get(
                            "title",
                            "",
                        ),
                        "similarity": similar.get(
                            "similarity",
                            0,
                        ),
                        "classification": classification,
                    }

                    if classification == "LIKELY_DUPLICATE":
                        likely_duplicates.append(entry)

                    elif classification == "HIGHLY_SIMILAR":
                        highly_similar.append(entry)

                    else:
                        related.append(entry)

            # -------------------------------------------------
            # Summary
            # -------------------------------------------------

            st.write("### Backlog Similarity Summary")

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Stories Analyzed",
                    len(backlog_stories),
                )

            with c2:
                st.metric(
                    "🔴 Likely Duplicates",
                    len(likely_duplicates),
                )

            with c3:
                st.metric(
                    "🟡 Highly Similar",
                    len(highly_similar),
                )

            with c4:
                st.metric(
                    "🔵 Related",
                    len(related),
                )

            # -------------------------------------------------
            # Likely duplicates
            # -------------------------------------------------

            if likely_duplicates:

                st.write(
                    "### 🔴 Likely Duplicate Stories"
                )

                for item in sorted(
                    likely_duplicates,
                    key=lambda x: x["similarity"],
                    reverse=True,
                ):

                    with st.container(border=True):

                        st.write(
                            f"**{item['source_id']}** — "
                            f"{item['source_title']}"
                        )

                        st.write(
                            f"↔ **{item['target_id']}** — "
                            f"{item['target_title']}"
                        )

                        st.error(
                            f"Similarity: {item['similarity']}% "
                            f"• Likely duplicate"
                        )

                        st.caption(
                            "💡 Consider merging, closing, or linking "
                            "these Jira stories before sprint planning."
                        )

            else:

                st.success(
                    "No likely duplicate stories detected "
                    "across the backlog."
                )

            # -------------------------------------------------
            # Highly similar
            # -------------------------------------------------

            if highly_similar:

                st.write(
                    "### 🟡 Highly Similar Stories"
                )

                for item in sorted(
                    highly_similar,
                    key=lambda x: x["similarity"],
                    reverse=True,
                ):

                    with st.container(border=True):

                        st.write(
                            f"**{item['source_id']}** — "
                            f"{item['source_title']}"
                        )

                        st.write(
                            f"↔ **{item['target_id']}** — "
                            f"{item['target_title']}"
                        )

                        st.warning(
                            f"Similarity: {item['similarity']}%"
                        )

            else:

                st.info(
                    "No highly similar stories detected "
                    "across the backlog."
                )

            st.caption(
                "Duplicate detection analyzes the complete Jira backlog, "
                "not only stories selected for the current sprint."
            )



            # -------------------------------------------------
            # Duplicate / Similar Story Detection
            # -------------------------------------------------

            try:
                similarity_response = requests.post(
                    "http://127.0.0.1:8000/api/v1/intelligence/stories/similar",
                    json={"stories": backlog.get("stories", [])},
                    timeout=120,
                )

                similarity_response.raise_for_status()

                similarity_data = similarity_response.json()

                st.session_state.similarity_results = {
                    item.get("primary_story", {}).get("id"): item
                    for item in similarity_data.get("groups", [])
                }

            except Exception as similarity_error:
                st.session_state.similarity_results = {}
                st.warning(
                    f"Duplicate detection unavailable: "
                    f"{similarity_error}"
                )


# ---------------------------------------------------------
# Display Team Plans
# ---------------------------------------------------------

if "team_plan" in st.session_state:

    team_plan = st.session_state.team_plan

    for team in team_plan.get("teams", []):

        with st.expander(
            f'👥 {team["team"]} — '
            f'{team["selected_points"]}/'
            f'{team["planning_capacity"]} points',
            expanded=True,
        ):

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Backlog",
                team["backlog_story_count"],
            )

            c2.metric(
                "Backlog Points",
                team["backlog_points"],
            )

            c3.metric(
                "Capacity",
                team["planning_capacity"],
            )

            c4.metric(
                "Planned",
                team["selected_points"],
            )

            # ---------------------------------------------
            # Capacity status
            # ---------------------------------------------

            if team["remaining_capacity"] > 0:

                st.info(
                    f'{team["remaining_capacity"]} points remain '
                    f'for this team.'
                )

            elif team["remaining_capacity"] == 0:

                st.success(
                    "Team capacity fully utilized."
                )

            else:

                st.warning(
                    f'Team is over capacity by '
                    f'{abs(team["remaining_capacity"])} points.'
                )


            # ---------------------------------------------
            # Selected Stories
            # ---------------------------------------------

            if team.get("selected_stories"):

                st.write("### Selected Stories")

                for story in team["selected_stories"]:

                    points = story.get("story_points", 0)

                    source = story.get(
                        "story_points_source",
                        "JIRA",
                    )

                    if source == "AI_ESTIMATED":
                        estimate_text = (
                            f"{points} pts 🤖 AI Estimated"
                        )
                    else:
                        estimate_text = (
                            f"{points} pts 🔵 Jira"
                        )

                    st.write(
                        f'**{story["id"]}** — '
                        f'{story["title"]} '
                        f'({estimate_text})'
                    )

                    if source == "AI_ESTIMATED":

                        confidence = story.get(
                            "ai_estimation_confidence"
                        )

                        reason = story.get(
                            "ai_estimation_reason"
                        )

                        if confidence is not None:
                            st.caption(
                                f"🤖 Qwen estimate | "
                                f"Confidence: {confidence}% | "
                                f"Cached: Yes"
                            )
                        else:
                            st.caption(
                                "🤖 Qwen estimated because Jira "
                                "does not have story points."
                            )

                        if reason:
                            st.caption(
                                f"Reason: {reason}"
                            )
            else:

                st.info(
                    "No stories selected for this team."
                )



            # ---------------------------------------------
            # Pull Requests for INREVIEW stories
            # ---------------------------------------------

            # Show PRs only when the current story is in review.
            story_status = story.get("status", "")

            if isinstance(story_status, dict):
                story_status = story_status.get("name", "")

            if str(story_status).upper().replace(" ", "") == "INREVIEW":

                pull_requests = story.get(
                    "pull_requests",
                    [],
                )

                with st.expander(
                    f"🔀 Pull Requests ({len(pull_requests)})",
                    expanded=bool(pull_requests),
                ):

                    if pull_requests:

                        for pr in pull_requests:

                            title = pr.get(
                                "title",
                                "Pull Request",
                            )

                            url = pr.get("url")
                            status = pr.get(
                                "status",
                                "UNKNOWN",
                            )

                            author = pr.get(
                                "author"
                            )

                            repository = pr.get(
                                "repository"
                            )

                            st.markdown(
                                f"**{title}**"
                            )

                            details = []

                            if repository:
                                details.append(
                                    f"📦 {repository}"
                                )

                            if author:
                                details.append(
                                    f"👤 {author}"
                                )

                            if status:
                                details.append(
                                    f"🔄 {status}"
                                )

                            if details:
                                st.caption(
                                    " • ".join(details)
                                )

                            if url:
                                st.link_button(
                                    "View Pull Request →",
                                    url,
                                )

                            st.divider()

                    else:
                        st.info(
                            "No pull request linked to this Jira issue."
                        )


            # ---------------------------------------------
            # Planning Decisions
            # ---------------------------------------------

            decisions = team.get(
                "decisions",
                [],
            )

            rejected_decisions = [
                decision
                for decision in decisions
                if not decision["selected"]
            ]

            if rejected_decisions:

                with st.expander(
                    "Planning decisions"
                ):

                    for decision in rejected_decisions:

                        st.write(
                            f'**{decision["story_id"]}**'
                        )

                        st.caption(
                            decision["reason"]
                        )

                        st.divider()


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    "AI Sprint Planning Assistant • "
    "Powered by Jira + FastAPI + Streamlit"
)

# ---------------------------------------------------------
