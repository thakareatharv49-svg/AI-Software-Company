from src.company.artifact_validation import validate_generated_artifacts


def test_accepts_nonempty_safe_relative_artifacts() -> None:
    assert validate_generated_artifacts({
        "index.html": '<link rel="stylesheet" href="style.css"><script src="app.js"></script>',
        "style.css": "body { color: black; }",
        "app.js": "console.log('ready');",
        "src/routes.py": "def health():\n    return {'status': 'ok'}\n",
    }) == []


def test_rejects_empty_artifact_sets_and_empty_files() -> None:
    assert "Generated project contains no deliverable files." in (
        validate_generated_artifacts({})
    )
    issues = validate_generated_artifacts({"index.html": "  "})
    assert any("index.html" in issue and "empty" in issue for issue in issues)


def test_rejects_absolute_and_traversal_paths() -> None:
    issues = validate_generated_artifacts({
        "../outside.py": "print('unsafe')",
        "/tmp/absolute.py": "print('unsafe')",
        "C:/outside.py": "print('unsafe')",
    })

    assert len(issues) == 3
    assert all("safe relative path" in issue for issue in issues)


def test_rejects_case_insensitive_path_collisions() -> None:
    issues = validate_generated_artifacts({
        "src/App.js": "export const app = true;",
        "src/app.js": "export const app = false;",
    })

    assert len(issues) == 1
    assert "collide on a case-insensitive filesystem" in issues[0]


def test_rejects_non_text_artifact_content() -> None:
    issues = validate_generated_artifacts({"app.js": None})  # type: ignore[dict-item]

    assert len(issues) == 1
    assert "non-text content" in issues[0]


def test_rejects_missing_local_browser_assets() -> None:
    issues = validate_generated_artifacts({
        "index.html": (
            '<link rel="stylesheet" href="styles/app.css">'
            '<script src="app.js"></script>'
        ),
        "styles/app.css": "body { background: url('../images/grid.svg'); }",
    })

    assert any("missing local asset 'app.js'" in issue for issue in issues)
    assert any("missing local asset '../images/grid.svg'" in issue for issue in issues)


def test_ignores_external_urls_and_client_side_routes() -> None:
    assert validate_generated_artifacts({
        "index.html": (
            '<a href="/settings">Settings</a>'
            '<script src="https://cdn.example.com/library.js"></script>'
        ),
    }) == []
