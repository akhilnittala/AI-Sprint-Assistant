import re


FIBONACCI_POINTS = [1, 2, 3, 5, 8, 13]


def _contains(text: str, words: list[str]) -> bool:
    text = text.lower()
    return any(
        re.search(
            rf"\\b{re.escape(word)}\\b",
            text,
        )
        for word in words
    )


def estimate_story_points(
    title: str,
    description: str = "",
    priority: str = "",
    labels: list[str] | None = None,
) -> int:
    """
    Estimate Jira story points when Jira has no estimate.

    This is intentionally deterministic so it works without an
    external LLM/API key. It uses Jira story information and maps
    complexity to Fibonacci-style story points.
    """

    labels = labels or []

    text = " ".join([
        title or "",
        description or "",
        priority or "",
        " ".join(labels),
    ]).lower()

    score = 0

    # -----------------------------------------------------
    # Very small / documentation / administrative work
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "documentation",
            "docs",
            "update document",
            "readme",
            "review document",
            "coverage",
            "configuration",
            "config",
        ],
    ):
        score += 1

    # -----------------------------------------------------
    # Testing / validation
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "test",
            "testing",
            "automation",
            "e2e",
            "integration test",
            "unit test",
            "validation",
        ],
    ):
        score += 1

    # -----------------------------------------------------
    # Implementation indicators
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "implement",
            "develop",
            "create",
            "add",
            "support",
            "enable",
            "introduce",
            "build",
            "modify",
            "change",
            "update",
        ],
    ):
        score += 2

    # -----------------------------------------------------
    # Infrastructure / Kubernetes / security complexity
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "kubernetes",
            "openshift",
            "operator",
            "controller",
            "webhook",
            "tls",
            "mtls",
            "security",
            "certificate",
            "redis",
            "argocd",
            "argo cd",
            "deployment",
            "statefulset",
            "helm",
        ],
    ):
        score += 2

    # -----------------------------------------------------
    # Multi-component / integration work
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "integration",
            "multiple components",
            "cross component",
            "end-to-end",
            "migration",
            "upgrade",
            "compatibility",
            "api",
        ],
    ):
        score += 2

    # -----------------------------------------------------
    # Explicit complexity indicators
    # -----------------------------------------------------
    if _contains(
        text,
        [
            "refactor",
            "redesign",
            "architecture",
            "breaking change",
            "performance",
            "scalability",
            "distributed",
        ],
    ):
        score += 3

    # -----------------------------------------------------
    # Large descriptions usually indicate more scope.
    # -----------------------------------------------------
    description_words = len(
        (description or "").split()
    )

    if description_words > 250:
        score += 3
    elif description_words > 120:
        score += 2
    elif description_words > 60:
        score += 1

    # -----------------------------------------------------
    # Priority can increase risk/complexity.
    # -----------------------------------------------------
    priority = (priority or "").upper()

    if priority == "HIGH":
        score += 1

    # -----------------------------------------------------
    # Map complexity to Fibonacci story points.
    # -----------------------------------------------------
    if score <= 1:
        return 1

    if score <= 3:
        return 2

    if score <= 5:
        return 3

    if score <= 7:
        return 5

    if score <= 10:
        return 8

    return 13
