import ast
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "app"


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
    assert (PACKAGE_ROOT / "services" / "__init__.py").is_file()
    assert (PACKAGE_ROOT / "services" / "account.py").is_file()
    assert (PACKAGE_ROOT / "services" / "auth.py").is_file()


def test_admin_does_not_import_api_endpoint_modules():
    imports = _imports_from(PACKAGE_ROOT / "admin" / "views.py")
    assert "app.api.auth" not in imports


def test_models_base_has_own_module():
    assert (PACKAGE_ROOT / "models" / "base.py").is_file()
    imports = _imports_from(PACKAGE_ROOT / "models" / "user.py")
    assert "app.models.base" in imports


def test_pytest_discovers_tests_package_only():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_tests_are_grouped_by_scope():
    assert (PROJECT_ROOT / "tests" / "unit").is_dir()
    assert (PROJECT_ROOT / "tests" / "integration").is_dir()
    assert not (PROJECT_ROOT / "unit_tests").exists()


def test_integration_user_setup_goes_through_helpers():
    integration_dir = PROJECT_ROOT / "tests" / "integration"
    excluded = {"conftest.py", "helpers.py"}

    for path in integration_dir.glob("test_*.py"):
        if path.name in excluded:
            continue
        source = path.read_text()
        assert "insert(User)" not in source


def test_main_registers_only_aggregate_api_router():
    imports = _imports_from(PACKAGE_ROOT / "main.py")

    assert "app.routing" in imports
    assert "app.api.account" not in imports
    assert "app.api.auth" not in imports
    assert "app.api.background" not in imports
    assert "app.api.files" not in imports
    assert "app.api.param_examples" not in imports
    assert "app.api.restful" not in imports
    assert "app.api.streaming" not in imports


def test_main_uses_single_health_handler():
    source = (PACKAGE_ROOT / "main.py").read_text()

    assert "async def health(" in source
    assert "async def health_post(" not in source


def test_api_business_contracts_live_in_schemas_package():
    user_api_imports = _imports_from(PACKAGE_ROOT / "api" / "users.py")
    auth_imports = _imports_from(PACKAGE_ROOT / "api" / "auth.py")
    user_api_source = (PACKAGE_ROOT / "api" / "users.py").read_text()
    auth_source = (PACKAGE_ROOT / "api" / "auth.py").read_text()

    assert "app.schemas.user" in user_api_imports
    assert "app.schemas.auth" in auth_imports
    assert "class UserCreate(" not in user_api_source
    assert "class UserUpdate(" not in user_api_source
    assert "class UserPatch(" not in user_api_source
    assert "class UserOut(" not in user_api_source
    assert "class LoginRequest(" not in auth_source


def test_api_router_names_match_module_purpose():
    account_source = (PACKAGE_ROOT / "api" / "account.py").read_text()

    assert "account_api = APIRouter" in account_source
    assert "data_api" not in account_source
    assert (PACKAGE_ROOT / "api" / "users.py").is_file()
    assert not (PACKAGE_ROOT / "api" / "restful.py").exists()


def test_user_model_uses_energy_not_balance():
    user_source = (PACKAGE_ROOT / "models" / "user.py").read_text()
    schema_source = (PACKAGE_ROOT / "schemas" / "user.py").read_text()
    account_schema_source = (PACKAGE_ROOT / "schemas" / "account.py").read_text()

    assert "energy" in user_source
    assert "balance" not in user_source
    assert "energy" in schema_source
    assert "balance" not in schema_source
    assert "energy" in account_schema_source
    assert "balance" not in account_schema_source


def test_account_service_uses_crud_verb_names():
    source = (PACKAGE_ROOT / "services" / "account.py").read_text()

    assert "async def list_accounts(" in source
    assert "async def create_account(" in source
    assert "async def read_account(" in source
    assert "async def update_account(" in source
    assert "async def delete_account(" in source
    assert "async def query_accounts(" in source
    assert "save_account" not in source
    assert "get_account" not in source
    assert "add_random_account" not in source
