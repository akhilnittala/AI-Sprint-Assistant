import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class StorySimilarity:

    TITLE_WEIGHT = 3
    DESCRIPTION_WEIGHT = 1
    ACCEPTANCE_WEIGHT = 2
    COMPONENT_WEIGHT = 2
    LABEL_WEIGHT = 2

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, list):
            return " ".join(str(item) for item in value)

        if isinstance(value, dict):
            return " ".join(str(v) for v in value.values())

        return str(value)

    def _normalize(self, text: str) -> str:
        text = text.lower()

        # Normalize common Jira terminology.
        text = text.replace("tlsv1.3", "tls 1.3")
        text = text.replace("tlsv1_3", "tls 1.3")

        # Keep letters, numbers and whitespace.
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        # Normalize whitespace.
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _field_text(
        self,
        story: dict[str, Any],
        field: str,
    ) -> str:
        return self._normalize(
            self._as_text(story.get(field, ""))
        )

    def _text(self, story: dict[str, Any]) -> str:
        """
        Build a weighted document.

        Repeating important fields gives them more influence
        in the TF-IDF representation.
        """

        title = self._field_text(story, "title")
        description = self._field_text(story, "description")
        acceptance = self._field_text(
            story,
            "acceptance_criteria",
        )
        component = self._field_text(
            story,
            "component",
        )
        labels = self._field_text(
            story,
            "labels",
        )

        parts = []

        if title:
            parts.extend([title] * self.TITLE_WEIGHT)

        if description:
            parts.extend(
                [description] * self.DESCRIPTION_WEIGHT
            )

        if acceptance:
            parts.extend(
                [acceptance] * self.ACCEPTANCE_WEIGHT
            )

        if component:
            parts.extend(
                [component] * self.COMPONENT_WEIGHT
            )

        if labels:
            parts.extend(
                [labels] * self.LABEL_WEIGHT
            )

        return " ".join(parts)

    def _classify(self, percentage: int) -> str:
        if percentage >= 90:
            return "LIKELY_DUPLICATE"

        if percentage >= 75:
            return "POTENTIAL_DUPLICATE"

        return "RELATED"

    def _common_terms(
        self,
        story_a: dict[str, Any],
        story_b: dict[str, Any],
    ) -> list[str]:

        text_a = set(
            self._normalize(
                self._as_text(story_a.get("title", ""))
                + " "
                + self._as_text(
                    story_a.get("acceptance_criteria", "")
                )
                + " "
                + self._as_text(
                    story_a.get("component", "")
                )
                + " "
                + self._as_text(
                    story_a.get("labels", "")
                )
            ).split()
        )

        text_b = set(
            self._normalize(
                self._as_text(story_b.get("title", ""))
                + " "
                + self._as_text(
                    story_b.get("acceptance_criteria", "")
                )
                + " "
                + self._as_text(
                    story_b.get("component", "")
                )
                + " "
                + self._as_text(
                    story_b.get("labels", "")
                )
            ).split()
        )

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "into",
            "should",
            "must",
            "allow",
            "able",
            "user",
            "users",
            "system",
        }

        common = {
            term
            for term in text_a.intersection(text_b)
            if len(term) >= 3 and term not in stop_words
        }

        return sorted(common)[:8]

    def _reason(
        self,
        story_a: dict[str, Any],
        story_b: dict[str, Any],
        percentage: int,
    ) -> str:

        common_terms = self._common_terms(
            story_a,
            story_b,
        )

        reasons = []

        component_a = self._normalize(
            self._as_text(story_a.get("component", ""))
        )

        component_b = self._normalize(
            self._as_text(story_b.get("component", ""))
        )

        if (
            component_a
            and component_b
            and component_a == component_b
        ):
            reasons.append("same component")

        labels_a = set(
            self._normalize(
                self._as_text(story_a.get("labels", ""))
            ).split()
        )

        labels_b = set(
            self._normalize(
                self._as_text(story_b.get("labels", ""))
            ).split()
        )

        common_labels = labels_a.intersection(labels_b)

        if common_labels:
            reasons.append(
                "shared labels: "
                + ", ".join(sorted(common_labels)[:5])
            )

        if common_terms:
            reasons.append(
                "shared concepts: "
                + ", ".join(common_terms)
            )

        if percentage >= 90:
            reasons.insert(
                0,
                "very high textual similarity",
            )
        elif percentage >= 75:
            reasons.insert(
                0,
                "high textual similarity",
            )
        else:
            reasons.insert(
                0,
                "related content",
            )

        return "; ".join(reasons)

    def analyze(
        self,
        stories: list[dict[str, Any]],
        threshold: float = 0.60,
    ) -> list[dict[str, Any]]:

        if len(stories) < 2:
            return []

        documents = [
            self._text(story)
            for story in stories
        ]

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )

        matrix = vectorizer.fit_transform(documents)
        scores = cosine_similarity(matrix)

        results = []

        for i, story in enumerate(stories):

            similar = []

            for j, candidate in enumerate(stories):

                if i == j:
                    continue

                score = float(scores[i][j])

                if score < threshold:
                    continue

                percentage = round(score * 100)

                classification = self._classify(
                    percentage
                )

                similar.append(
                    {
                        "story_id": candidate.get("id"),
                        "title": candidate.get("title"),
                        "similarity": percentage,
                        "classification": classification,
                        "reason": self._reason(
                            story,
                            candidate,
                            percentage,
                        ),
                    }
                )

            similar.sort(
                key=lambda item: item["similarity"],
                reverse=True,
            )

            results.append(
                {
                    "story_id": story.get("id"),
                    "title": story.get("title"),
                    "similar_stories": similar[:5],
                }
            )

        return results
