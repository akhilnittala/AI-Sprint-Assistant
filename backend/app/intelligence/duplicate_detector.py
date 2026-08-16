from typing import Any

from backend.app.intelligence.similarity import StorySimilarity


class DuplicateDetector:

    DUPLICATE_THRESHOLD = 90
    POTENTIAL_DUPLICATE_THRESHOLD = 75

    def __init__(self):
        self.similarity = StorySimilarity()

    def detect(
        self,
        stories: list[dict[str, Any]],
    ) -> dict[str, Any]:

        results = self.similarity.analyze(
            stories,
            threshold=0.60,
        )

        groups = []
        potential_groups = []

        seen_duplicates = set()
        seen_potential = set()

        story_map = {
            story.get("id"): story
            for story in stories
        }

        for result in results:

            story_id = result.get("story_id")

            if not story_id:
                continue

            similar = result.get(
                "similar_stories",
                [],
            )

            duplicates = [
                item
                for item in similar
                if item["similarity"]
                >= self.DUPLICATE_THRESHOLD
            ]

            potential_duplicates = [
                item
                for item in similar
                if (
                    self.POTENTIAL_DUPLICATE_THRESHOLD
                    <= item["similarity"]
                    < self.DUPLICATE_THRESHOLD
                )
            ]

            # ---------------------------------------------
            # Likely duplicates
            # ---------------------------------------------

            if duplicates and story_id not in seen_duplicates:

                group = {
                    "primary_story": {
                        "id": story_id,
                        "title": result.get("title"),
                    },
                    "duplicates": duplicates,
                }

                groups.append(group)

                seen_duplicates.add(story_id)

                for item in duplicates:
                    seen_duplicates.add(
                        item["story_id"]
                    )

            # ---------------------------------------------
            # Potential duplicates
            # ---------------------------------------------

            if (
                potential_duplicates
                and story_id not in seen_potential
            ):

                group = {
                    "primary_story": {
                        "id": story_id,
                        "title": result.get("title"),
                    },
                    "potential_duplicates": (
                        potential_duplicates
                    ),
                }

                potential_groups.append(group)

                seen_potential.add(story_id)

                for item in potential_duplicates:
                    seen_potential.add(
                        item["story_id"]
                    )

        return {
            "groups": groups,
            "potential_groups": potential_groups,
            "total_groups": len(groups),
            "total_potential_groups": len(
                potential_groups
            ),
            "analyzed_stories": len(stories),
        }
