import ast
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "app"
APPS_ROOT = PACKAGE_ROOT / "apps"
ACCOUNTS_ROOT = APPS_ROOT / "accounts"
COMMON_ROOT = PACKAGE_ROOT / "common"
EXAMPLES_ROOT = APPS_ROOT / "examples"
FILE_MANAGER_ROOT = APPS_ROOT / "file_manager"
APP_TEST_ROOTS = [ACCOUNTS_ROOT / "tests", EXAMPLES_ROOT / "tests", FILE_MANAGER_ROOT / "tests"]


def _imports_from(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_service_layer_modules_exist():
    assert (ACCOUNTS_ROOT / "services" / "__init__.py").is_file()
    assert (ACCOUNTS_ROOT / "services" / "account.py").is_file()
    assert (ACCOUNTS_ROOT / "services" / "auth.py").is_file()


def test_common_modules_hold_shared_infrastructure():
    assert (COMMON_ROOT / "config.py").is_file()
    assert (COMMON_ROOT / "db.py").is_file()
    assert (COMMON_ROOT / "security" / "token.py").is_file()
    assert (COMMON_ROOT / "security" / "password.py").is_file()
    assert (COMMON_ROOT / "deps" / "pagination").is_dir()


def test_non_account_apps_only_import_accounts_or_themselves():
    violations: list[tuple[str, str]] = []

    for path in APPS_ROOT.rglob("*.py"):
        rel = path.relative_to(APPS_ROOT)
        if len(rel.parts) < 2:
            continue
        current_app = rel.parts[0]
        if current_app == "accounts":
            continue
        for imported in _imports_from(path):
            parts = imported.split(".")
            if parts[:2] == ["app", "apps"] and len(parts) >= 3 and parts[2] not in {current_app, "accounts"}:
                violations.append((str(path.relative_to(PROJECT_ROOT)), imported))

    assert violations == []


def test_common_does_not_import_apps():
    violations: list[tuple[str, str]] = []

    for path in COMMON_ROOT.rglob("*.py"):
        for imported in _imports_from(path):
            if imported == "app.apps" or imported.startswith("app.apps."):
                violations.append((str(path.relative_to(PROJECT_ROOT)), imported))

    assert violations == []


def test_admin_does_not_import_api_endpoint_modules():
    imports = _imports_from(ACCOUNTS_ROOT / "admin" / "views.py")
    assert "app.apps.accounts.api.auth" not in imports


def test_models_base_has_own_module():
    assert (ACCOUNTS_ROOT / "models" / "base.py").is_file()
    imports = _imports_from(ACCOUNTS_ROOT / "models" / "user.py")
    assert "app.apps.accounts.models.base" in imports


def test_pytest_discovers_tests_and_file_manager_packages():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["tool"]["pytest"]["ini_options"]["testpaths"] == [
        "tests",
        "app/apps/accounts/tests",
        "app/apps/examples/tests",
        "app/apps/file_manager/tests",
    ]


def test_tests_are_grouped_by_scope():
    assert (PROJECT_ROOT / "tests" / "unit").is_dir()
    assert (PROJECT_ROOT / "tests" / "integration").is_dir()
    assert not (PROJECT_ROOT / "unit_tests").exists()


def test_app_tests_live_with_app_packages():
    for app_tests in APP_TEST_ROOTS:
        assert app_tests.is_dir()
        assert (app_tests / "__init__.py").is_file()

    app_specific_root_test_names = {
        "test_account.py",
        "test_account_schema.py",
        "test_account_service.py",
        "test_admin_auth.py",
        "test_auth.py",
        "test_auth_deps.py",
        "test_auth_service.py",
        "test_files_api.py",
        "test_pagination.py",
        "test_param_examples.py",
        "test_password_hash.py",
        "test_password_length_validation.py",
        "test_recent_fastapi_examples.py",
        "test_restful_users.py",
    }
    root_matches = [
        str(path.relative_to(PROJECT_ROOT))
        for path in (PROJECT_ROOT / "tests").rglob("test_*.py")
        if path.name in app_specific_root_test_names or path.name.startswith("test_file_manager")
    ]

    assert root_matches == []


def test_integration_user_setup_goes_through_helpers():
    excluded = {"conftest.py", "helpers.py"}

    for integration_dir in [PROJECT_ROOT / "tests" / "integration", ACCOUNTS_ROOT / "tests" / "integration"]:
        for path in integration_dir.glob("test_*.py"):
            if path.name in excluded:
                continue
            source = path.read_text()
            assert "insert(User)" not in source


def test_main_registers_only_aggregate_api_router():
    imports = _imports_from(PACKAGE_ROOT / "main.py")

    assert "app.routing" in imports
    assert "app.apps.accounts.router" not in imports
    assert "app.apps.examples.router" not in imports
    assert "app.apps.accounts.api.account" not in imports
    assert "app.apps.accounts.api.auth" not in imports
    assert "app.apps.examples.api.background" not in imports
    assert "app.apps.examples.api.files" not in imports
    assert "app.apps.examples.api.param_examples" not in imports
    assert "app.apps.examples.api.streaming" not in imports


def test_main_uses_single_health_handler():
    source = (PACKAGE_ROOT / "main.py").read_text()

    assert "async def health(" in source
    assert "async def health_post(" not in source


def test_api_business_contracts_live_in_schemas_package():
    user_api_imports = _imports_from(ACCOUNTS_ROOT / "api" / "users.py")
    auth_imports = _imports_from(ACCOUNTS_ROOT / "api" / "auth.py")
    user_api_source = (ACCOUNTS_ROOT / "api" / "users.py").read_text()
    auth_source = (ACCOUNTS_ROOT / "api" / "auth.py").read_text()

    assert "app.apps.accounts.schemas.user" in user_api_imports
    assert "app.apps.accounts.schemas.auth" in auth_imports
    assert "class UserCreate(" not in user_api_source
    assert "class UserUpdate(" not in user_api_source
    assert "class UserPatch(" not in user_api_source
    assert "class UserOut(" not in user_api_source
    assert "class LoginRequest(" not in auth_source


def test_api_router_names_match_module_purpose():
    account_source = (ACCOUNTS_ROOT / "api" / "account.py").read_text()

    assert "account_api = APIRouter" in account_source
    assert "data_api" not in account_source
    assert (ACCOUNTS_ROOT / "api" / "users.py").is_file()
    assert not (ACCOUNTS_ROOT / "api" / "restful.py").exists()


def test_user_model_uses_energy_not_balance():
    user_source = (ACCOUNTS_ROOT / "models" / "user.py").read_text()
    schema_source = (ACCOUNTS_ROOT / "schemas" / "user.py").read_text()
    account_schema_source = (ACCOUNTS_ROOT / "schemas" / "account.py").read_text()

    assert "energy" in user_source
    assert "balance" not in user_source
    assert "energy" in schema_source
    assert "balance" not in schema_source
    assert "energy" in account_schema_source
    assert "balance" not in account_schema_source


def test_account_service_uses_crud_verb_names():
    source = (ACCOUNTS_ROOT / "services" / "account.py").read_text()

    assert "async def list_accounts(" in source
    assert "async def create_account(" in source
    assert "async def read_account(" in source
    assert "async def update_account(" in source
    assert "async def delete_account(" in source
    assert "async def query_accounts(" in source
    assert "save_account" not in source
    assert "get_account" not in source
    assert "add_random_account" not in source
