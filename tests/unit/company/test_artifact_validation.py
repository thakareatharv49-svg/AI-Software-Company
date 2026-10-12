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


def test_resolves_assets_relative_to_nested_stylesheets() -> None:
    assert validate_generated_artifacts({
        "index.html": '<link rel="stylesheet" href="styles/app.css">',
        "styles/app.css": "body { background: url('../images/grid.svg'); }",
        "images/grid.svg": '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
    }) == []


def test_rejects_missing_srcset_and_css_import_assets() -> None:
    issues = validate_generated_artifacts({
        "index.html": '<img srcset="images/small.webp 1x, images/large.webp 2x">',
        "style.css": '@import "theme.css"; .hero { background: url("hero.webp"); }',
    })

    assert any("images/small.webp" in issue for issue in issues)
    assert any("images/large.webp" in issue for issue in issues)
    assert any("theme.css" in issue for issue in issues)
    assert any("hero.webp" in issue for issue in issues)


def test_srcset_data_urls_do_not_create_false_missing_asset_errors() -> None:
    assert validate_generated_artifacts({
        "index.html": '<img srcset="data:image/gif;base64,AAAA 1x, small.webp 2x">',
        "small.webp": "image-bytes-placeholder",
    }) == []
