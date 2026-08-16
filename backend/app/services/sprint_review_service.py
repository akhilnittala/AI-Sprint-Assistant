
from pathlib import Path
from datetime import datetime
import re
import requests

from backend.app.services.jira_service import JiraService


class SprintReviewService:

    def __init__(self):
        self.jira = JiraService()

    def get_active_sprints(self):
        """
        Return active/current Jira sprints for Sprint Review.

        Prefer Jira Agile API, but fall back to the board's issue data
        because some Jira configurations do not expose active sprints
        correctly through /rest/agile/1.0/board/{id}/sprint.
        """

        board_id = int(
            __import__("os").environ.get(
                "JIRA_BOARD_ID",
                "400",
            )
        )

        # ---------------------------------------------------------
        # 1. Preferred: Jira Agile active-sprint endpoint
        # ---------------------------------------------------------
        try:
            response = requests.get(
                f"{self.jira.url}/rest/agile/1.0/board/"
                f"{board_id}/sprint",
                params={
                    "state": "active",
                    "maxResults": 50,
                },
                auth=self.jira.auth,
                headers=self.jira.headers,
                timeout=30,
            )

            if response.ok:
                values = response.json().get("values", [])

                if values:
                    return values

        except Exception as e:
            print(
                f"⚠️ Agile active-sprint lookup failed: {e}"
            )

        # ---------------------------------------------------------
        # 2. Fallback: discover sprints from board issues
        # ---------------------------------------------------------
        try:
            response = requests.get(
                f"{self.jira.url}/rest/agile/1.0/board/"
                f"{board_id}/issue",
                params={
                    "startAt": 0,
                    "maxResults": 100,
                    "fields": "summary,status",
                },
                auth=self.jira.auth,
                headers=self.jira.headers,
                timeout=30,
            )

            response.raise_for_status()

            issues = response.json().get(
                "issues",
                [],
            )

            discovered = {}

            # Jira sprint custom field is discovered dynamically.
            sprint_field_id = self.jira._find_sprint_field()

            if not sprint_field_id:
                print(
                    "⚠️ Jira Sprint custom field not found"
                )
                return []

            # Get issue details including Sprint field.
            response = requests.get(
                f"{self.jira.url}/rest/agile/1.0/board/"
                f"{board_id}/issue",
                params={
                    "startAt": 0,
                    "maxResults": 1000,
                    "fields": sprint_field_id,
                },
                auth=self.jira.auth,
                headers=self.jira.headers,
                timeout=60,
            )

            response.raise_for_status()

            issues = response.json().get(
                "issues",
                [],
            )

            for issue in issues:
                fields = issue.get("fields", {})

                sprint_value = fields.get(
                    sprint_field_id
                )

                if not sprint_value:
                    continue

                if not isinstance(
                    sprint_value,
                    list,
                ):
                    sprint_value = [
                        sprint_value
                    ]

                for sprint in sprint_value:

                    if not isinstance(
                        sprint,
                        dict,
                    ):
                        continue

                    sprint_id = sprint.get("id")

                    if not sprint_id:
                        continue

                    state = str(
                        sprint.get(
                            "state",
                            ""
                        )
                    ).lower()

                    if state != "active":
                        continue

                    discovered[str(sprint_id)] = {
                        "id": sprint_id,
                        "name": sprint.get(
                            "name",
                            f"Sprint {sprint_id}",
                        ),
                        "state": "ACTIVE",
                        "startDate": sprint.get(
                            "startDate"
                        ),
                        "endDate": sprint.get(
                            "endDate"
                        ),
                        "originBoardId": sprint.get(
                            "originBoardId",
                            board_id,
                        ),
                    }

            result = list(
                discovered.values()
            )

            if result:
                print(
                    f"✅ Discovered {len(result)} active "
                    f"sprint(s) from Jira board issues"
                )

            return result

        except Exception as e:
            print(
                f"❌ Unable to discover active sprints: {e}"
            )
            return []

    def _get_sprint_issues(self, sprint_id):
        board_id = int(
            __import__("os").environ.get(
                "JIRA_BOARD_ID",
                "400",
            )
        )

        issues = []
        start_at = 0

        while True:
            response = requests.get(
                f"{self.jira.url}/rest/agile/1.0/board/"
                f"{board_id}/sprint/{sprint_id}/issue",
                params={
                    "startAt": start_at,
                    "maxResults": 100,
                    "fields": (
                        "summary,status,assignee,"
                        "priority,labels,customfield_10028"
                    ),
                },
                auth=self.jira.auth,
                headers=self.jira.headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()
            page = data.get("issues", [])

            issues.extend(page)

            if not page:
                break

            start_at += len(page)

            if start_at >= data.get("total", 0):
                break

        return issues

    def _get_comments(self, issue_key):
        response = requests.get(
            f"{self.jira.url}/rest/api/3/issue/"
            f"{issue_key}/comment",
            params={
                "orderBy": "-created",
                "maxResults": 10,
            },
            auth=self.jira.auth,
            headers=self.jira.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json().get("comments", [])

    @staticmethod
    def _extract_comment_text(comment):
        body = comment.get("body", {})

        if isinstance(body, str):
            return body

        parts = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    parts.append(node.get("text", ""))

                for child in node.get("content", []):
                    walk(child)

            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(body)

        return " ".join(parts).strip()

    @staticmethod
    def _comment_status(text, jira_status):
        text_lower = text.lower()

        if any(
            x in text_lower
            for x in [
                "blocked",
                "blocker",
                "blocked by",
                "cannot proceed",
                "can't proceed",
                "waiting for dependency",
            ]
        ):
            return "BLOCKED"

        if any(
            x in text_lower
            for x in [
                "ready for testing",
                "ready for test",
                "ready for qa",
                "qa validation",
            ]
        ):
            return "READY_FOR_TESTING"

        if any(
            x in text_lower
            for x in [
                "in testing",
                "testing in progress",
                "under testing",
            ]
        ):
            return "IN_TESTING"

        if any(
            x in text_lower
            for x in [
                "ready for review",
                "ready to review",
                "code review",
            ]
        ):
            return "READY_FOR_REVIEW"

        if any(
            x in text_lower
            for x in [
                "completed",
                "complete",
                "fixed",
                "resolved",
                "done",
        ]):
            return "COMPLETED"

        if any(
            x in text_lower
            for x in [
                "waiting",
                "awaiting",
                "pending",
            ]
        ):
            return "WAITING"

        return jira_status.upper().replace(" ", "_")

    def generate_review(self, sprint_id):
        sprints = self.get_active_sprints()

        sprint = next(
            (
                item
                for item in sprints
                if int(item["id"]) == int(sprint_id)
            ),
            None,
        )

        if not sprint:
            raise ValueError(
                f"Active sprint {sprint_id} was not found."
            )

        issues = self._get_sprint_issues(sprint_id)

        closed = []
        in_progress = []
        review = []
        other = []

        for issue in issues:
            fields = issue.get("fields", {})

            status_obj = fields.get("status") or {}
            status = status_obj.get(
                "name",
                "Unknown",
            )

            assignee_obj = fields.get("assignee")

            assignee = (
                assignee_obj.get("displayName")
                if assignee_obj
                else "Unassigned"
            )

            points = fields.get("customfield_10028")

            if points is None:
                points = 0

            comments = self._get_comments(
                issue["key"]
            )

            latest_comment = ""

            comment_author = ""

            comment_date = ""

            if comments:
                latest = comments[-1]

                latest_comment = (
                    self._extract_comment_text(
                        latest
                    )
                )

                author = latest.get("author") or {}

                comment_author = author.get(
                    "displayName",
                    "",
                )

                comment_date = latest.get(
                    "created",
                    "",
                )

            comment_status = self._comment_status(
                latest_comment,
                status,
            )

            item = {
                "key": issue["key"],
                "title": fields.get(
                    "summary",
                    "",
                ),
                "status": status,
                "comment_status": comment_status,
                "assignee": assignee,
                "story_points": int(float(points)),
                "latest_comment": latest_comment,
                "comment_author": comment_author,
                "comment_date": comment_date,
                "pull_requests": self.jira.get_pull_requests(
                    issue["id"]
                ),
            }

            normalized = status.lower()

            if normalized in {
                "done",
                "closed",
                "resolved",
            }:
                closed.append(item)

            elif normalized in {
                "in progress",
                "in_progress",
            }:
                in_progress.append(item)

            elif normalized in {
                "review",
                "in review",
            }:
                review.append(item)

            else:
                other.append(item)

        return {
            "sprint": {
                "id": sprint["id"],
                "name": sprint["name"],
                "state": sprint.get(
                    "state",
                    "active",
                ),
                "start_date": sprint.get(
                    "startDate"
                ),
                "end_date": sprint.get(
                    "endDate"
                ),
            },
            "summary": {
                "total": len(issues),
                "closed": len(closed),
                "in_progress": len(in_progress),
                "review": len(review),
                "other": len(other),
            },
            "closed": closed,
            "in_progress": in_progress,
            "review": review,
            "other": other,
        }

    @staticmethod
    def generate_markdown(report):
        sprint = report["sprint"]
        summary = report["summary"]

        lines = [
            f"# Sprint Review — {sprint['name']}",
            "",
            f"**Sprint ID:** {sprint['id']}",
            f"**State:** {sprint['state']}",
            "",
            "## Summary",
            "",
            f"- Total issues: {summary['total']}",
            f"- Closed: {summary['closed']}",
            f"- In Progress: {summary['in_progress']}",
            f"- In Review: {summary['review']}",
            f"- Other: {summary['other']}",
            "",
        ]

        def add_section(title, items):
            lines.extend([
                f"## {title}",
                "",
            ])

            if not items:
                lines.append("No items.")
                lines.append("")
                return

            for item in items:
                lines.extend([
                    f"### {item['key']} — {item['title']}",
                    "",
                    f"- **Assignee:** {item['assignee']}",
                    f"- **Jira Status:** {item['status']}",
                    f"- **Comment Status:** {item['comment_status']}",
                    f"- **Story Points:** {item['story_points']}",
                ])

                if item["latest_comment"]:
                    lines.append(
                        f"- **Latest Comment:** "
                        f"{item['latest_comment']}"
                    )

                if item["comment_author"]:
                    lines.append(
                        f"- **Comment By:** "
                        f"{item['comment_author']}"
                    )

                lines.append("")

        add_section(
            "Completed / Closed",
            report["closed"],
        )

        add_section(
            "In Progress",
            report["in_progress"],
        )

        add_section(
            "In Review",
            report["review"],
        )

        add_section(
            "Other Sprint Items",
            report["other"],
        )

        return "\n".join(lines)
