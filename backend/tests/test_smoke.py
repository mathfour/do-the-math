"""Phase 0 smoke test — proves the pytest harness runs."""


def test_harness_runs():
    assert True


def test_app_package_importable():
    import app  # noqa: F401
