from app.common.security.password import make_password, verify_password


def test_make_password_returns_hash():
    hashed = make_password("mypassword")
    assert isinstance(hashed, str)
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)


def test_verify_password_correct():
    hashed = make_password("correct-password")
    assert verify_password("correct-password", hashed) is True


def test_verify_password_wrong():
    hashed = make_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_different_passwords_produce_different_hashes():
    h1 = make_password("password-a")
    h2 = make_password("password-b")
    assert h1 != h2
