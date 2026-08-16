from typing import Dict, List



class StoryIntelligence:

    def analyze(self, story) -> Dict:
        title = self._get(story, "title", "")
        description = self._get(story, "description", "")
        acceptance_criteria = self._get(story, "acceptance_criteria", "")

        quality = self._quality_score(
            title,
            description,
            acceptance_criteria,
        )

        risks = self._detect_risks(story)
        dependencies = self._detect_dependencies(story)
        complexity = self._complexity(story)

        readiness = self._readiness_score(
            quality["score"],
            risks,
            dependencies,
            complexity,
        )

        return {
            "story_id": self._get(story, "id", self._get(story, "key", "")),
            "title": title,
            "quality_score": quality["score"],
            "quality_status": quality["status"],
            "quality_issues": quality["issues"],
            "risk_score": risks["score"],
            "risk_level": risks["level"],
            "risk_factors": risks["factors"],
            "dependencies": dependencies,
            "complexity": complexity,
            "readiness_score": readiness["score"],
            "readiness_status": readiness["status"],
            "recommendation": readiness["recommendation"],
        }

    def analyze_many(self, stories: List) -> List[Dict]:
        return [self.analyze(story) for story in stories]

    def _quality_score(self, title, description, acceptance_criteria):
        score = 0
        issues = []

        if title and len(title.strip()) >= 10:
            score += 20
        else:
            issues.append("Story title is missing or too vague.")

        if description and len(description.strip()) >= 50:
            score += 20
        else:
            issues.append("Description is missing or too short.")

        if acceptance_criteria:
            score += 30
        else:
            issues.append("Acceptance criteria are missing.")

        if self._is_testable(description, acceptance_criteria):
            score += 15
        else:
            issues.append("Story does not contain clearly testable behavior.")

        if self._is_specific(title, description):
            score += 15
        else:
            issues.append("Story contains vague or non-specific requirements.")

        if score >= 85:
            status = "READY"
        elif score >= 70:
            status = "NEEDS_REFINEMENT"
        elif score >= 50:
            status = "RISKY"
        else:
            status = "NOT_READY"

        return {
            "score": min(score, 100),
            "status": status,
            "issues": issues,
        }

    def _is_specific(self, title, description):
        """
        Determine whether a story is specific enough to implement.

        This intentionally does NOT treat words such as "support",
        "update", or "modify" as automatically vague. Those words
        are perfectly valid in technical Jira stories.

        Specificity is determined from the overall content.
        """

        title = (title or "").strip()
        description = (description or "").strip()

        text = f"{title} {description}".lower()

        score = 0

        # -------------------------------------------------
        # 1. Title quality
        # -------------------------------------------------

        if len(title) >= 15:
            score += 20

        # -------------------------------------------------
        # 2. Description detail
        # -------------------------------------------------

        if len(description) >= 50:
            score += 20

        if len(description) >= 150:
            score += 10

        # -------------------------------------------------
        # 3. Technical component
        # -------------------------------------------------

        technical_components = [
            "api",
            "operator",
            "controller",
            "webhook",
            "redis",
            "argocd",
            "argo cd",
            "kubernetes",
            "deployment",
            "service",
            "configmap",
            "secret",
            "crd",
            "tls",
            "certificate",
            "authentication",
            "authorization",
            "database",
            "repository",
            "repo-server",
            "server",
            "prometheus",
            "dex",
        ]

        if any(component in text for component in technical_components):
            score += 15

        # -------------------------------------------------
        # 4. Expected behavior
        # -------------------------------------------------

        behavior_terms = [
            "should",
            "must",
            "shall",
            "when",
            "allow",
            "prevent",
            "reject",
            "accept",
            "return",
            "create",
            "delete",
            "update",
            "configure",
            "apply",
            "validate",
            "enable",
            "disable",
        ]

        if any(term in text for term in behavior_terms):
            score += 20

        # -------------------------------------------------
        # 5. Measurable / testable outcome
        # -------------------------------------------------

        measurable_terms = [
            "test",
            "verify",
            "expected",
            "acceptance",
            "success",
            "failure",
            "error",
            "status",
            "metric",
            "response",
            "within",
            "less than",
            "greater than",
        ]

        if any(term in text for term in measurable_terms):
            score += 15

        # -------------------------------------------------
        # 6. Penalize genuinely vague phrases
        # -------------------------------------------------

        vague_phrases = [
            "improve performance",
            "make better",
            "improve things",
            "handle appropriately",
            "fix issue",
            "fix problems",
            "improve usability",
            "enhance performance",
            "optimize things",
            "update as needed",
            "modify as needed",
        ]

        vague_count = sum(
            phrase in text
            for phrase in vague_phrases
        )

        score -= vague_count * 15

        # -------------------------------------------------
        # Final decision
        # -------------------------------------------------

        return score >= 45

    def _is_testable(self, description, acceptance_criteria):
        text = f"{description} {acceptance_criteria}".lower()

        terms = [
            "should",
            "must",
            "when",
            "given",
            "then",
            "expected",
            "verify",
            "test",
            "acceptance",
        ]

        return any(term in text for term in terms)

    def _detect_risks(self, story):
        score = 0
        factors = []

        text = " ".join([
            str(self._get(story, "title", "")),
            str(self._get(story, "description", "")),
        ]).lower()

        if any(x in text for x in ["tls", "security", "authentication"]):
            score += 15
            factors.append("Security-sensitive change")

        if any(x in text for x in ["production", "upgrade", "migration"]):
            score += 20
            factors.append("Production or migration impact")

        if any(x in text for x in ["api", "crd", "operator"]):
            score += 10
            factors.append("Platform/API change")

        if any(x in text for x in ["redis", "database", "storage"]):
            score += 15
            factors.append("Stateful component")

        if any(x in text for x in [
            "cross team",
            "another team",
            "dependency",
        ]):
            score += 20
            factors.append("Cross-team dependency")

        if not self._get(story, "acceptance_criteria", ""):
            score += 10
            factors.append("Missing acceptance criteria")

        score = min(score, 100)

        if score >= 70:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "score": score,
            "level": level,
            "factors": factors,
        }

    def _detect_dependencies(self, story):
        dependencies = []

        explicit = self._get(story, "dependencies", None)

        if explicit:
            if isinstance(explicit, list):
                dependencies.extend(str(x) for x in explicit)
            else:
                dependencies.append(str(explicit))

        text = " ".join([
            str(self._get(story, "title", "")),
            str(self._get(story, "description", "")),
        ]).lower()

        terms = [
            "depends on",
            "blocked by",
            "requires",
            "after",
            "prerequisite",
        ]

        if any(term in text for term in terms):
            dependencies.append(
                "Potential dependency detected from story text"
            )

        return dependencies

    def _complexity(self, story):
        text = " ".join([
            str(self._get(story, "title", "")),
            str(self._get(story, "description", "")),
        ]).lower()

        score = 0
        factors = []

        indicators = {
            "API/CRD change": ["api", "crd"],
            "Kubernetes change": [
                "kubernetes",
                "operator",
                "deployment",
            ],
            "Security/TLS": [
                "tls",
                "security",
                "authentication",
            ],
            "Stateful component": [
                "redis",
                "database",
                "storage",
            ],
            "Integration testing": [
                "integration",
                "e2e",
            ],
            "Migration": [
                "migration",
                "upgrade",
            ],
        }

        for name, terms in indicators.items():
            if any(term in text for term in terms):
                score += 15
                factors.append(name)

        if len(text) > 1000:
            score += 15
            factors.append("Large requirement")

        score = min(score, 100)

        if score >= 60:
            level = "HIGH"
            suggested_points = 8
        elif score >= 30:
            level = "MEDIUM"
            suggested_points = 5
        else:
            level = "LOW"
            suggested_points = 2

        return {
            "score": score,
            "level": level,
            "suggested_points": suggested_points,
            "factors": factors,
        }

    def _readiness_score(
        self,
        quality_score,
        risks,
        dependencies,
        complexity,
    ):
        score = quality_score

        if risks["level"] == "HIGH":
            score -= 10
        elif risks["level"] == "MEDIUM":
            score -= 5

        if dependencies:
            score -= 5

        if complexity["level"] == "HIGH":
            score -= 5

        score = max(0, min(score, 100))

        if score >= 85:
            status = "READY"
            recommendation = "Safe candidate for sprint planning."
        elif score >= 70:
            status = "NEEDS_REFINEMENT"
            recommendation = "Refine the story before committing."
        elif score >= 50:
            status = "RISKY"
            recommendation = "Plan only if the team accepts the risk."
        else:
            status = "NOT_READY"
            recommendation = "Do not commit until the story is refined."

        return {
            "score": score,
            "status": status,
            "recommendation": recommendation,
        }

    @staticmethod
    def _get(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)

        return getattr(obj, name, default)
