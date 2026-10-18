from __future__ import annotations

from src.company.product_quality import (
    find_exposed_secrets,
    find_missing_product_tests,
    find_uncovered_mission_features,
    find_unfinished_product_content,
    find_weak_javascript_tests,
    find_weak_product_tests,
)


def test_detects_obvious_placeholder_copy_in_generated_ui() -> None:
    issues = find_unfinished_product_content({
        "index.html": "<main><h1>Coming soon</h1></main>",
        "app.js": "startApp();",
    })

    assert len(issues) == 1
    assert "index.html" in issues[0]
    assert "unfinished placeholder text" in issues[0]


def test_ignores_legitimate_todo_labels_and_input_placeholders() -> None:
    issues = find_unfinished_product_content({
        "index.html": '<label>To-do list</label><input placeholder="Add a task">',
        "app.js": 'const label = "TODO";',
    })

    assert issues == []


def test_ignores_tests_and_documentation() -> None:
    issues = find_unfinished_product_content({
        "tests/test_copy.py": 'assert "coming soon" in source',
        "docs/README.md": "Lorem ipsum is a placeholder example.",
    })

    assert issues == []


def test_detects_unimplemented_feature_copy_in_javascript() -> None:
    issues = find_unfinished_product_content({
        "app.js": 'showMessage("Feature not available yet");',
    })

    assert len(issues) == 1
    assert "app.js" in issues[0]

    
def test_rejects_assertions_that_compare_only_literal_values() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": "def test_title():\n    assert \"Expense Tracker\" in \"Expense Tracker\"\n"
    })

    assert len(issues) == 1
    assert "tautological assertion" in issues[0]


def test_accepts_assertions_that_exercise_runtime_values() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def test_total_uses_expenses():\n"
            "    expenses = [{\"amount\": 12}, {\"amount\": 8}]\n"
            "    total = sum(item[\"amount\"] for item in expenses)\n"
            "    assert total == 20\n"
            "    assert total != 0\n"
        )
    })

    assert issues == []


def test_rejects_constant_boolean_assertion() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": "def test_app():\n    assert True\n"
    })

    assert len(issues) == 1


def test_rejects_generated_smoke_only_test_suite() -> None:
    issues = find_weak_product_tests({
        "tests/test_generated_project.py": (
            "from pathlib import Path\n"
            "def test_browser_entrypoint_and_local_assets_exist():\n"
            "    assert Path('index.html').is_file()\n"
        )
    })

    assert len(issues) == 1
    assert "only generated smoke checks" in issues[0]
    assert "behavioral tests" in issues[0]


def test_accepts_generated_smoke_check_when_behavior_test_is_also_present() -> None:
    issues = find_weak_product_tests({
        "tests/test_generated_project.py": (
            "from pathlib import Path\n"
            "def test_browser_entrypoint_and_local_assets_exist():\n"
            "    assert Path('index.html').is_file()\n"
            "def test_total_uses_expenses():\n"
            "    expenses = [12, 8]\n"
            "    assert sum(expenses) == 20\n"
        )
    })

    assert issues == []



def test_rejects_generated_test_function_without_assertions() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def test_add_expense():\n"
            "    create_expense(amount=12)\n"
        )
    })

    assert len(issues) == 1
    assert "without an explicit assertion" in issues[0]
    assert "test_add_expense" in issues[0]


def test_accepts_expected_exception_check_without_plain_assert() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "import pytest\n"
            "def test_rejects_negative_amount():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_expense(-1)\n"
        )
    })

    assert issues == []


def test_accepts_behavior_test_that_uses_assertion_helper() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def assert_valid_note(note):\n"
            "    assert note['title'].strip()\n"
            "    assert isinstance(note['body'], str)\n"
            "def test_create_note():\n"
            "    note = create_note('Plan', 'Study')\n"
            "    assert_valid_note(note)\n"
        )
    })

    assert issues == []


def test_rejects_test_that_calls_non_asserting_helper_only() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def make_note():\n"
            "    return {'title': 'Plan'}\n"
            "def test_create_note():\n"
            "    make_note()\n"
        )
    })

    assert len(issues) == 1
    assert "without an explicit assertion" in issues[0]


def test_rejects_generated_test_module_without_test_functions() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def build_sample_note():\n"
            "    return {'title': 'Plan'}\n"
        )
    })

    assert len(issues) == 1
    assert "contain no test functions" in issues[0]


def test_accepts_non_test_helper_module_without_test_functions() -> None:
    issues = find_weak_product_tests({
        "tests/helpers.py": (
            "def build_sample_note():\n"
            "    return {'title': 'Plan'}\n"
        )
    })

    assert issues == []


def test_ignores_tautology_examples_in_comments_when_behavior_is_tested() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "# Avoid weak tests such as assert True or assert 1 == 1.\n"
            "def test_total_uses_expenses():\n"
            "    expenses = [12, 8]\n"
            "    assert sum(expenses) == 20\n"
        )
    })

    assert issues == []



def test_rejects_smoke_only_tests_in_large_mission_test_project_filename() -> None:
    issues = find_weak_product_tests({
        "tests/test_project.py": (
            "from pathlib import Path\n"
            "def test_browser_entrypoint_and_local_assets_exist():\n"
            "    assert Path('index.html').is_file()\n"
            "def test_generated_source_files_exist():\n"
            "    assert Path('app.js').is_file()\n"
        )
    })

    assert len(issues) == 1
    assert "only generated smoke checks" in issues[0]
    assert "mission-specific behavioral tests" in issues[0]


def test_accepts_behavioral_tests_in_large_mission_test_project_filename() -> None:
    issues = find_weak_product_tests({
        "tests/test_project.py": (
            "def test_total_uses_expenses():\n"
            "    expenses = [12, 8]\n"
            "    assert sum(expenses) == 20\n"
            "def test_rejects_negative_expense():\n"
            "    import pytest\n"
            "    with pytest.raises(ValueError):\n"
            "        add_expense(-1)\n"
        )
    })

    assert issues == []



def test_rejects_file_existence_only_tests_with_generic_names() -> None:
    issues = find_weak_product_tests({
        "tests/test_project.py": (
            "from pathlib import Path\n"
            "def test_app_is_present():\n"
            "    assert Path('index.html').is_file()\n"
            "def test_script_is_present():\n"
            "    assert Path('app.js').exists()\n"
        )
    })

    assert len(issues) == 1
    assert "only generated smoke checks" in issues[0]


def test_accepts_file_smoke_check_alongside_behavior_test() -> None:
    issues = find_weak_product_tests({
        "tests/test_project.py": (
            "from pathlib import Path\n"
            "def test_app_is_present():\n"
            "    assert Path('index.html').is_file()\n"
            "def test_total_uses_expenses():\n"
            "    expenses = [12, 8]\n"
            "    assert sum(expenses) == 20\n"
        )
    })

    assert issues == []



def test_rejects_project_with_no_automated_test_files() -> None:
    issues = find_missing_product_tests({
        "index.html": "<main>Inventory</main>",
        "app.js": "function addItem(items, item) { return [...items, item]; }",
    })

    assert len(issues) == 1
    assert "no automated test files" in issues[0]
    assert "behavioral tests" in issues[0]


def test_rejects_project_with_only_documentation_not_tests() -> None:
    issues = find_missing_product_tests({
        "README.md": "# Product",
        "docs/QA.md": "Tests should cover create, update, and delete.",
        "src/app.py": "def add_item(items, item):\n    return [*items, item]\n",
    })

    assert len(issues) == 1
    assert "no automated test files" in issues[0]



def test_requires_test_modules_for_broad_product_delivery() -> None:
    issues = find_missing_product_tests({
        "index.html": "<main>Inventory</main>",
        "app.js": "function addItem(items, item) { return [...items, item]; }",
    })

    assert len(issues) == 1
    assert "no automated test files" in issues[0]


def test_accepts_project_with_a_test_module() -> None:
    issues = find_missing_product_tests({
        "src/app.py": "def add_item(items, item):\n    return [*items, item]\n",
        "tests/test_app.py": (
            "from src.app import add_item\n"
            "def test_add_item():\n"
            "    assert add_item([], 'x') == ['x']\n"
        ),
    })

    assert issues == []



def test_accepts_javascript_and_typescript_test_conventions() -> None:
    issues = find_missing_product_tests({
        "src/app.js": "export function addItem(items, item) { return [...items, item]; }",
        "src/app.test.js": "import { expect, test } from 'vitest';",
        "src/components/Notes.spec.tsx": "import { describe, it } from 'vitest';",
    })

    assert issues == []


def test_does_not_treat_javascript_source_or_docs_as_tests() -> None:
    issues = find_missing_product_tests({
        "src/test_helpers.js": "export const testMode = false;",
        "docs/testing.md": "Use app.test.js for tests.",
        "app.js": "function start() {}",
    })

    assert len(issues) == 1
    assert "no automated test files" in issues[0]


def test_detects_high_confidence_credentials_in_shipped_source() -> None:
    issues = find_exposed_secrets({
        "app.py": "GITHUB_TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz1234567890'",
        "infra/config.py": "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'",
        "src/client.js": "const apiKey = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDE';",
    })

    assert len(issues) == 3
    assert any("GitHub personal access token" in issue for issue in issues)
    assert any("AWS access key ID" in issue for issue in issues)
    assert any("OpenAI-style API key" in issue for issue in issues)


def test_detects_private_key_material_in_shipped_source() -> None:
    issues = find_exposed_secrets({
        "config/server.pem": "-----BEGIN PRIVATE KEY-----\\nexample\\n-----END PRIVATE KEY-----",
    })

    assert len(issues) == 1
    assert "private key material" in issues[0]


def test_ignores_documentation_and_test_fixtures_for_secret_scan() -> None:
    issues = find_exposed_secrets({
        "docs/security.md": "Example token: ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        "tests/test_security.py": "assert 'AKIAIOSFODNN7EXAMPLE' in sample",
        ".env.example": "OPENAI_API_KEY=replace-with-environment-secret",
        "src/settings.py": "API_KEY = os.environ.get('OPENAI_API_KEY', '')",
    })

    assert issues == []


def test_detects_requested_features_missing_from_generated_tests() -> None:
    objective = "Create, edit, delete, search and pin notes with persistent local storage and input validation."
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_notes.py": (
                "def test_create_note(): pass\n"
                "def test_search_notes(): pass\n"
            ),
        },
    )

    assert any("edit/update" in issue for issue in issues)
    assert any("delete/remove" in issue for issue in issues)
    assert any("pin/favorite" in issue for issue in issues)
    assert any("persistence" in issue for issue in issues)
    assert any("validation" in issue for issue in issues)


def test_accepts_test_traceability_for_requested_product_workflows() -> None:
    objective = "Create, edit, delete and search notes with persistent local storage and validation."
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_notes.py": (
                "def test_create_note(): pass\n"
                "def test_update_note(): pass\n"
                "def test_delete_note(): pass\n"
                "def test_search_notes(): pass\n"
                "def test_localstorage_persistence(): pass\n"
                "def test_validation_rejects_invalid_note(): pass\n"
            ),
        },
    )

    assert issues == []



def test_rejects_empty_javascript_test_bodies() -> None:
    issues = find_weak_javascript_tests({
        "tests/notes.test.js": "test('creates a note', () => {});",
    })

    assert len(issues) == 1
    assert "empty test body" in issues[0]


def test_rejects_tautological_javascript_assertions() -> None:
    issues = find_weak_javascript_tests({
        "tests/app.spec.js": "it('works', () => { expect(true).toBe(true); });",
    })

    assert len(issues) == 1
    assert "tautological assertion" in issues[0]


def test_accepts_javascript_test_that_checks_product_behavior() -> None:
    issues = find_weak_javascript_tests({
        "tests/notes.test.js": (
            "test('adds a note', () => {\\n"
            "  const notes = addNote([], { title: 'Study' });\\n"
            "  expect(notes).toHaveLength(1);\\n"
            "  expect(notes[0].title).toBe('Study');\\n"
            "});"
        ),
    })

    assert issues == []



def test_feature_traceability_normalizes_windows_paths_and_nested_js_tests() -> None:
    objective = "Create, edit, delete, and search records with persistent storage."
    issues = find_uncovered_mission_features(
        objective,
        {
            r"src\\features\\__tests__\\records.test.mjs": (
                "test('create record', () => {}); "
                "test('edit record', () => {}); "
                "test('delete record', () => {}); "
                "test('search record', () => {}); "
                "test('storage persistence', () => {});"
            ),
        },
    )

    assert issues == []


def test_feature_traceability_does_not_treat_source_helpers_as_tests() -> None:
    objective = "Create and delete records."
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_records.py": "def createRecord(): pass; def deleteRecord(): pass",
            "src/records.js": "export function createRecord() {} export function deleteRecord() {}",
        },
    )

    assert any("create" in issue for issue in issues)
    assert any("delete/remove" in issue for issue in issues)



def test_rejects_empty_javascript_test_using_function_callback() -> None:
    issues = find_weak_javascript_tests({
        "src/records.test.js": "test('creates a record', function () {});",
    })

    assert len(issues) == 1
    assert "empty test body" in issues[0]


def test_rejects_empty_modern_javascript_test_modules() -> None:
    issues = find_weak_javascript_tests({
        "src/features/records.test.mjs": "test('creates a record', () => {});",
        "src/features/auth.spec.cjs": "it('rejects invalid login', function () {});",
    })

    assert len(issues) == 2
    assert all("empty test body" in issue for issue in issues)


def test_accepts_behavior_assertions_in_modern_javascript_test_modules() -> None:
    issues = find_weak_javascript_tests({
        "src/features/records.test.mjs": (
            "test('creates a record', () => { "
            "expect(createRecord('Plan').title).toBe('Plan'); });"
        ),
        "src/features/auth.spec.cjs": (
            "it('rejects invalid login', () => { "
            "assert.equal(validateLogin(''), false); });"
        ),
    })

    assert issues == []


def test_accepts_javascript_test_with_behavior_assertion() -> None:
    issues = find_weak_javascript_tests({
        "src/records.test.js": (
            "test('creates a record', function () { "
            "assert.equal(createRecord('Plan').title, 'Plan'); });"
        ),
    })

    assert issues == []


def test_rejects_javascript_test_that_only_calls_product_code() -> None:
    issues = find_weak_javascript_tests({
        "src/records.test.js": (
            "test('creates a record', () => { createRecord('Plan'); });"
        ),
    })

    assert len(issues) == 1
    assert "without an explicit assertion" in issues[0]


def test_accepts_javascript_test_with_nested_behavior_assertion() -> None:
    issues = find_weak_javascript_tests({
        "src/records.test.js": (
            "test('creates a record', () => { "
            "expect(createRecord('Plan').title).toBe('Plan'); });"
        ),
    })

    assert issues == []



def test_feature_traceability_covers_common_multi_feature_workflows() -> None:
    objective = (
        "Sort records, confirm deletion, show an empty state, support responsive "
        "mobile layout, display notifications, and allow undo."
    )
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_records.py": (
                "def test_sort_records(): pass\n"
                "def test_delete_confirmation(): pass\n"
                "def test_empty_state(): pass\n"
                "def test_responsive_mobile_layout(): pass\n"
                "def test_notifications(): pass\n"
            ),
        },
    )

    assert len(issues) == 1
    assert "undo/redo" in issues[0]


def test_feature_traceability_accepts_covered_extended_workflows() -> None:
    objective = (
        "Sort records, confirm deletion, show an empty state, support responsive "
        "mobile layout, display notifications, and allow undo."
    )
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_records.py": (
                "def test_sort_records(): pass\n"
                "def test_delete_confirmation(): pass\n"
                "def test_empty_state(): pass\n"
                "def test_responsive_mobile_layout(): pass\n"
                "def test_notifications(): pass\n"
                "def test_undo_last_change(): pass\n"
            ),
        },
    )

    assert issues == []


def test_feature_traceability_ignores_comments_and_helper_names_as_coverage() -> None:
    objective = "Create and delete records."
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_records.py": (
                "# test_create_record and test_delete_record are planned here\n"
                "def create_record():\n    return {}\n"
                "def delete_record():\n    return True\n"
                "def test_records_are_available():\n    assert True\n"
            ),
        },
    )

    assert any("create" in issue for issue in issues)
    assert any("delete/remove" in issue for issue in issues)


def test_feature_traceability_accepts_named_javascript_test_titles() -> None:
    objective = "Create and delete records."
    issues = find_uncovered_mission_features(
        objective,
        {
            "src/records.spec.mjs": (
                "test('creates a record', () => { expect(createRecord()).toBeTruthy(); });\n"
                "it('deletes a record', () => { expect(deleteRecord()).toBe(true); });"
            ),
        },
    )

    assert issues == []


def test_feature_traceability_covers_common_product_workflows() -> None:
    objective = (
        "Build a responsive dashboard with notifications, analytics, pagination, "
        "accessibility, role-based permissions, API integration, backup and restore, "
        "recurring scheduling, and payments."
    )
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_dashboard.py": (
                "def test_responsive_layout(): pass\n"
                "def test_notifications_are_sent(): pass\n"
                "def test_analytics_report(): pass\n"
                "def test_pagination_limits_results(): pass\n"
                "def test_accessibility_labels(): pass\n"
                "def test_role_permissions(): pass\n"
                "def test_api_integration(): pass\n"
                "def test_backup_and_restore(): pass\n"
                "def test_recurring_schedule(): pass\n"
                "def test_payment_checkout(): pass\n"
            )
        },
    )

    assert issues == []


def test_feature_traceability_reports_uncovered_common_workflows() -> None:
    issues = find_uncovered_mission_features(
        "Add notifications, analytics, pagination, accessibility, and payments.",
        {
            "tests/test_app.py": (
                "def test_notifications_are_sent(): pass\n"
                "def test_payment_checkout(): pass\n"
            )
        },
    )

    assert any("analytics/reporting" in issue for issue in issues)
    assert any("pagination" in issue for issue in issues)
    assert any("accessibility" in issue for issue in issues)



def test_feature_traceability_covers_more_product_workflows() -> None:
    objective = (
        "Support real-time collaboration, offline mode, file uploads, "
        "multi-tenancy, audit logging, charts, and bulk operations."
    )
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_app.py": (
                "def test_realtime_collaboration_syncs_shared_changes(): pass\\n"
                "def test_offline_mode_saves_changes(): pass\\n"
                "def test_file_uploads_validate_attachments(): pass\\n"
                "def test_workspace_tenants_are_isolated(): pass\\n"
                "def test_audit_logging_records_changes(): pass\\n"
                "def test_charts_visualize_activity(): pass\\n"
                "def test_bulk_operations_update_records(): pass\\n"
            )
        },
    )

    assert issues == []


def test_feature_traceability_reports_missing_upload_and_tenant_tests() -> None:
    issues = find_uncovered_mission_features(
        "Add file uploads and multi-tenancy to the app.",
        {
            "tests/test_app.py": (
                "def test_upload_button_is_visible(): pass\\n"
            )
        },
    )

    assert any("file uploads" in issue for issue in issues)
    assert any("multi-tenancy" in issue for issue in issues)
