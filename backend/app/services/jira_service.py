import os
import re

import requests
from dotenv import load_dotenv

from backend.app.models.story import Story
from backend.app.ai.story_point_estimator import estimate_story_points

load_dotenv(".env")


class JiraService:
    def __init__(self):
        self.url = os.environ["JIRA_URL"].rstrip("/")
        self.email = os.environ["JIRA_EMAIL"]
        self.api_token = os.environ["JIRA_API_TOKEN"]
        self.project_key = os.environ["JIRA_PROJECT_KEY"]

        self.auth = (self.email, self.api_token)

        self.headers = {
            "Accept": "application/json",
        }

    @staticmethod
    def _extract_team_from_sprint(sprint_value):
        """
        Extract team from Jira sprint name.

        Examples:
            GitOps Tangerine Sprint 37 -> Tangerine
            GitOps Crimson Sprint 37   -> Crimson
            GitOps Scarlet Sprint 38   -> Scarlet
        """

        if not sprint_value:
            return "Unassigned"

        sprint_names = []

        if isinstance(sprint_value, list):
            for sprint in sprint_value:
                if isinstance(sprint, dict):
                    name = sprint.get("name")
                    if name:
                        sprint_names.append(str(name))
                elif sprint:
                    sprint_names.append(str(sprint))

        elif isinstance(sprint_value, dict):
            name = sprint_value.get("name")
            if name:
                sprint_names.append(str(name))

        else:
            sprint_names.append(str(sprint_value))

        # Prefer the latest matching sprint in the field.
        for sprint_name in reversed(sprint_names):
            match = re.search(
                r"^GitOps\s+([A-Za-z0-9_-]+)\s+Sprint\s+\d+",
                sprint_name,
                re.IGNORECASE,
            )

            if match:
                return match.group(1).strip().title()

        return "Unassigned"

    def _find_sprint_field(self):
        response = requests.get(
            f"{self.url}/rest/api/3/field",
            auth=self.auth,
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

        for field in response.json():
            if field.get("name", "").strip().lower() == "sprint":
                return field["id"]

        return None

    def get_pull_requests(self, issue_id):
        """
        Extract PRs associated with a Jira issue.

        Sources:
          1. Git Pull Request custom field (customfield_10875)
          2. Docs Pull Request custom field (customfield_10964)
          3. Jira comments

        This is intentionally called only for INREVIEW issues
        during Sprint Review processing.
        """

        pull_requests = []
        seen_urls = set()

        def add_pr(url, title="Pull Request", author=None):
            if not url:
                return

            url = str(url).strip().rstrip(".,);]}>'\"")

            # Jira smart-links may contain both the canonical PR URL
            # and a /changes URL for the same pull request.
            import re as _re
            match = _re.match(
                r"(https?://github\.com/[^/]+/[^/]+/pull/[0-9]+)",
                url,
            )
            if match:
                url = match.group(1)

            if not url.startswith(("http://", "https://")):
                return

            if url in seen_urls:
                return

            seen_urls.add(url)

            pull_requests.append({
                "title": title or "Pull Request",
                "url": url,
                "status": "UNKNOWN",
                "author": author,
                "repository": None,
            })

        def extract_urls(value):
            """
            Extract complete URLs from Jira custom fields/comments.

            Supports Jira smart links such as:
              [https://github.com/org/repo/pull/123|display text|smart-link]

            and plain URLs.
            """
            if value is None:
                return []

            if isinstance(value, str):
                urls = []

                # -------------------------------------------------
                # Jira smart-link format:
                # [URL|display text|smart-link]
                # -------------------------------------------------
                for match in re.findall(
                    r'\[([^\]\|]+)\|[^\]]*\]',
                    value,
                ):
                    candidate = match.strip()

                    if candidate.startswith(
                        ("http://", "https://")
                    ):
                        urls.append(candidate)

                # -------------------------------------------------
                # Plain URLs
                # -------------------------------------------------
                for match in re.findall(
                    r'https?://[^\s<>"\'\[\]\|]+',
                    value,
                ):
                    urls.append(match)

                # -------------------------------------------------
                # Normalize and remove duplicates.
                # -------------------------------------------------
                result = []

                for url in urls:
                    url = (
                        url
                        .strip()
                        .rstrip(".,);]}>'\"")
                    )

                    if url.startswith(
                        ("http://", "https://")
                    ) and url not in result:
                        result.append(url)

                return result

            if isinstance(value, dict):
                urls = []

                for key in (
                    "url",
                    "link",
                    "href",
                    "self",
                ):
                    if value.get(key):
                        urls.extend(
                            extract_urls(value.get(key))
                        )

                for item in value.values():
                    if isinstance(
                        item,
                        (dict, list),
                    ):
                        urls.extend(
                            extract_urls(item)
                        )

                return list(dict.fromkeys(urls))

            if isinstance(value, list):
                urls = []

                for item in value:
                    urls.extend(
                        extract_urls(item)
                    )

                return list(dict.fromkeys(urls))

            return []

        try:
            response = requests.get(
                f"{self.url}/rest/api/2/issue/{issue_id}",
                params={
                    "fields": (
                        "summary,"
                        "comment,"
                        "customfield_10875,"
                        "customfield_10964"
                    ),
                },
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                timeout=20,
            )

            response.raise_for_status()

            issue = response.json()
            fields = issue.get("fields", {})

            if not isinstance(fields, dict):
                return pull_requests

            # -------------------------------------------------
            # 1. Git Pull Request
            # -------------------------------------------------

            git_pr = fields.get("customfield_10875")

            for url in extract_urls(git_pr):
                add_pr(
                    url,
                    "Git Pull Request",
                )

            # -------------------------------------------------
            # 2. Docs Pull Request
            # -------------------------------------------------

            docs_pr = fields.get("customfield_10964")

            for url in extract_urls(docs_pr):
                add_pr(
                    url,
                    "Docs Pull Request",
                )

            # -------------------------------------------------
            # 3. Jira comments
            # -------------------------------------------------

            comments = fields.get("comment", {})

            if isinstance(comments, dict):
                comments = comments.get(
                    "comments",
                    [],
                )

            if not isinstance(comments, list):
                comments = []

            for comment in comments:

                if not isinstance(comment, dict):
                    continue

                body = comment.get(
                    "body",
                    "",
                )

                # Jira Server/DC normally returns text.
                if isinstance(body, str):
                    text = body

                # Jira Cloud may return structured content.
                else:
                    text = str(body)

                author_data = comment.get(
                    "author",
                    {},
                )

                author = None

                if isinstance(author_data, dict):
                    author = (
                        author_data.get(
                            "displayName"
                        )
                        or author_data.get(
                            "name"
                        )
                        or author_data.get(
                            "emailAddress"
                        )
                    )

                for url in extract_urls(text):
                    add_pr(
                        url,
                        "Pull Request from Jira comment",
                        author,
                    )

            return pull_requests

        except Exception as e:
            print(
                f"Warning: unable to extract PRs "
                f"from Jira issue {issue_id}: {e}"
            )
            return pull_requests

    def get_sprint_review(self, sprint_id):
        """
        Build Sprint Review data for ONE sprint only.

        This deliberately does NOT use get_backlog(), so Sprint Review
        doesn't process the entire Jira backlog.
        """
        try:
            # Fetch only issues belonging to the selected sprint.
            jql = f'project = "{self.project_key}" AND sprint = {sprint_id} ORDER BY key'

            response = requests.get(
                f"{self.url}/rest/api/2/search",
                params={
                    "jql": jql,
                    "maxResults": 1000,
                    "fields": "*all",
                },
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            issues = data.get("issues", [])

            done = []
            in_review = []
            in_progress = []

            def status_name(fields):
                value = fields.get("status", "")

                if isinstance(value, dict):
                    return str(value.get("name", ""))

                return str(value or "")

            def normalize_status(value):
                return (
                    str(value)
                    .upper()
                    .replace("_", "")
                    .replace("-", "")
                    .replace(" ", "")
                )

            for issue in issues:
                fields = issue.get("fields", {})

                if not isinstance(fields, dict):
                    continue

                key = issue.get("key")
                title = fields.get("summary", "")
                status = status_name(fields)
                normalized = normalize_status(status)

                assignee = fields.get("assignee")
                if isinstance(assignee, dict):
                    assignee = (
                        assignee.get("displayName")
                        or assignee.get("name")
                        or assignee.get("emailAddress")
                    )

                item = {
                    "key": key,
                    "title": title,
                    "status": status,
                    "assignee": assignee or "Unassigned",
                    "url": f"{self.url}/browse/{key}",
                    "pull_requests": [],
                }

                # Only call Jira development APIs for IN REVIEW.
                if normalized in {
                    "INREVIEW",
                    "REVIEW",
                    "CODEVIEW",
                    "CODEREVIEW",
                }:
                    item["pull_requests"] = self.get_pull_requests(
                        issue.get("id") or key
                    )
                    in_review.append(item)

                elif normalized in {
                    "DONE",
                    "CLOSED",
                    "RESOLVED",
                }:
                    done.append(item)

                elif normalized in {
                    "INPROGRESS",
                    "INDEVELOPMENT",
                }:
                    in_progress.append(item)

            # Resolve sprint name without scanning the backlog.
            sprint_name = str(sprint_id)

            try:
                sprint_response = requests.get(
                    f"{self.url}/rest/greenhopper/1.0/sprint/{sprint_id}",
                    auth=(self.email, self.api_token),
                    headers={"Accept": "application/json"},
                    timeout=15,
                )

                if sprint_response.ok:
                    sprint_data = sprint_response.json()
                    sprint_name = (
                        sprint_data.get("name")
                        or sprint_name
                    )
            except Exception:
                pass

            return {
                "sprint_id": str(sprint_id),
                "sprint_name": sprint_name,
                "summary": {
                    "done": len(done),
                    "in_review": len(in_review),
                    "in_progress": len(in_progress),
                    "total": len(done) + len(in_review) + len(in_progress),
                },
                "done": done,
                "in_review": in_review,
                "in_progress": in_progress,
            }

        except Exception as e:
            print(f"Error loading sprint review for sprint {sprint_id}: {e}")
            raise


    def get_backlog(self):
        """
        Load the Jira board's planning universe.

        Board 400 is the source of truth:
          - Scrum backlog
          - Active sprint issues

        Active sprint issues are included so the UI can show the
        complete Jira planning picture, but they are marked with
        sprint information and are NOT treated as new backlog work
        by the sprint planner.

        Jira board backlog excludes active/future sprint issues,
        therefore we explicitly load active sprints as well.
        """

        BOARD_ID = int(
            os.environ.get(
                "JIRA_BOARD_ID",
                "400",
            )
        )

        sprint_field_id = self._find_sprint_field()

        fields = (
            "summary,description,priority,status,"
            "labels,components,customfield_10028"
        )

        if sprint_field_id:
            fields += f",{sprint_field_id}"

        issues_by_key = {}

        def fetch_paginated(url, params):
            """
            Jira Agile REST API pagination.

            Agile board backlog/sprint issue endpoints use
            startAt/maxResults pagination rather than the
            nextPageToken mechanism used by /rest/api/3/search/jql.
            """

            start_at = 0
            page_size = 100

            while True:
                request_params = dict(params)
                request_params["startAt"] = start_at
                request_params["maxResults"] = page_size

                response = requests.get(
                    url,
                    params=request_params,
                    auth=self.auth,
                    headers=self.headers,
                    timeout=30,
                )

                response.raise_for_status()

                data = response.json()
                page = data.get("issues", [])

                for issue in page:
                    issues_by_key[issue["key"]] = issue

                total = data.get("total", 0)

                if not page:
                    break

                start_at += len(page)

                if start_at >= total:
                    break


        # =====================================================
        # 1. Jira board backlog
        # =====================================================

        fetch_paginated(
            f"{self.url}/rest/agile/1.0/board/"
            f"{BOARD_ID}/backlog",
            {
                "maxResults": 100,
                "fields": fields,
            },
        )

        backlog_count = len(issues_by_key)

        # =====================================================
        # 2. Active sprints on the board
        # =====================================================

        sprint_response = requests.get(
            f"{self.url}/rest/agile/1.0/board/"
            f"{BOARD_ID}/sprint",
            params={
                "state": "active",
                "maxResults": 50,
            },
            auth=self.auth,
            headers=self.headers,
            timeout=30,
        )

        sprint_response.raise_for_status()

        active_sprints = sprint_response.json().get(
            "values",
            []
        )

        active_sprint_ids = {
            sprint["id"]
            for sprint in active_sprints
        }

        # =====================================================
        # 3. Load all active sprint issues
        # =====================================================

        for sprint in active_sprints:

            sprint_id = sprint["id"]

            fetch_paginated(
                f"{self.url}/rest/agile/1.0/board/"
                f"{BOARD_ID}/sprint/{sprint_id}/issue",
                {
                    "maxResults": 100,
                    "fields": fields,
                },
            )

        # =====================================================
        # 4. Convert Jira issues to Story objects
        # =====================================================

        stories = []

        for issue in issues_by_key.values():

            fields_data = issue.get(
                "fields",
                {},
            )

            story_points = fields_data.get(
                "customfield_10028"
            )

            # Jira may return 0 or None for an unestimated story.
            if story_points in (None, ""):
                jira_story_points = None
            else:
                try:
                    jira_story_points = int(
                        float(story_points)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    jira_story_points = None

            description = fields_data.get(
                "description"
            )

            if isinstance(
                description,
                dict,
            ):
                description = self._extract_description(
                    description
                )

            if not description:
                description = ""

            jira_priority = fields_data.get(
                "priority"
            )

            if isinstance(
                jira_priority,
                dict,
            ):
                jira_priority = jira_priority.get(
                    "name",
                    "UNDEFINED",
                )
            else:
                jira_priority = "UNDEFINED"

            priority_map = {
                "CRITICAL": "HIGH",
                "MAJOR": "HIGH",
                "NORMAL": "MEDIUM",
                "MINOR": "LOW",
                "TRIVIAL": "LOW",
                "UNDEFINED": "MEDIUM",
            }

            priority = priority_map.get(
                str(jira_priority).upper(),
                "MEDIUM",
            )

            jira_status = fields_data.get(
                "status"
            )

            if isinstance(
                jira_status,
                dict,
            ):
                jira_status = jira_status.get(
                    "name",
                    "TODO",
                )
            else:
                jira_status = "TODO"

            status_map = {
                "TO DO": "TODO",
                "OPEN": "TODO",
                "NEW": "TODO",
                "TODO": "TODO",
                "IN PROGRESS": "IN_PROGRESS",
                "IN_PROGRESS": "IN_PROGRESS",

                # Jira workflow status used by GitOps.
                "REVIEW": "INREVIEW",
                "IN REVIEW": "INREVIEW",
                "IN-REVIEW": "INREVIEW",
                "IN_REVIEW": "INREVIEW",
                "CODE REVIEW": "INREVIEW",

                "DONE": "DONE",
                "CLOSED": "DONE",
                "RESOLVED": "DONE",
            }

            status = status_map.get(
                str(jira_status).upper(),
                "TODO",
            )

            sprint_value = (
                fields_data.get(
                    sprint_field_id
                )
                if sprint_field_id
                else None
            )

            team = self._extract_team_from_sprint(
                sprint_value
            )

            # -------------------------------------------------
            # Determine whether this issue belongs to an
            # active sprint.
            # -------------------------------------------------

            active_sprint = None

            sprint_values = []

            if isinstance(
                sprint_value,
                list,
            ):
                sprint_values = sprint_value

            elif sprint_value:
                sprint_values = [
                    sprint_value
                ]

            for sprint_item in sprint_values:

                if not isinstance(
                    sprint_item,
                    dict,
                ):
                    continue

                if sprint_item.get(
                    "id"
                ) in active_sprint_ids:

                    active_sprint = sprint_item
                    break

            # -------------------------------------------------
            # Story points
            #
            # IMPORTANT:
            # AI estimation should happen here only when Jira
            # has no usable estimate.
            # -------------------------------------------------

            ai_estimated_points = None
            story_points_source = "JIRA"

            if jira_story_points is None:

                try:
                    from backend.app.services.story_estimation_service import (
                        estimate_story_points,
                    )

                    ai_estimated_points = (
                        estimate_story_points(
                            title=fields_data.get(
                                "summary",
                                "",
                            ),
                            description=description,
                            priority=str(
                                jira_priority
                                or ""
                            ),
                            labels=fields_data.get(
                                "labels",
                                [],
                            ),
                        )
                    )

                except ImportError:
                    # Estimator is optional. Keep zero until
                    # the estimation service is configured.
                    ai_estimated_points = 0

                story_points = (
                    ai_estimated_points or 0
                )

                story_points_source = (
                    "AI_ESTIMATED"
                    if ai_estimated_points
                    else "JIRA"
                )

            else:
                story_points = jira_story_points

            story = Story(
                id=issue["key"],
                title=fields_data.get(
                    "summary",
                    "",
                ),
                description=description,
                story_points=int(
                    story_points
                ),
                priority=priority.upper(),
                status=status,
                team=team,
                dependencies=[],
                labels=fields_data.get(
                    "labels",
                    [],
                ),
                pull_requests=(
                    self.get_pull_requests(issue["id"])
                    if status == "INREVIEW"
                    else []
                ),
            )

            # These attributes are exposed to the API/UI without
            # changing the core Story model yet.
            story.story_points_source = (
                story_points_source
            )
            story.ai_estimated_points = (
                ai_estimated_points
            )
            story.jira_story_points = (
                jira_story_points
            )
            story.active_sprint = (
                active_sprint.get("name")
                if active_sprint
                else None
            )

            stories.append(story)

        print(
            f"Jira board {BOARD_ID}: "
            f"{backlog_count} backlog + "
            f"{len(issues_by_key) - backlog_count} "
            f"active-sprint issues = "
            f"{len(stories)} unique issues"
        )

        return stories

    @staticmethod
    def _extract_description(description):
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

        walk(description)

        return " ".join(parts)
