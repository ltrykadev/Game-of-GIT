from gameofgit.engine.sandbox import Sandbox


def test_sandbox_path_exists_inside_with():
    with Sandbox() as s:
        assert s.path.is_dir()


def test_sandbox_path_removed_after_with():
    with Sandbox() as s:
        p = s.path
    assert not p.exists()


def test_sandbox_close_is_idempotent():
    s = Sandbox()
    s.close()
    s.close()  # second call must not raise


def test_sandbox_cleans_up_on_exception_inside_with():
    p = None
    try:
        with Sandbox() as s:
            p = s.path
            assert p.is_dir()
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert p is not None
    assert not p.exists()


def test_sandbox_path_is_unique_per_instance():
    with Sandbox() as a, Sandbox() as b:
        assert a.path != b.path


def test_sandbox_prefix_is_gog():
    with Sandbox() as s:
        assert s.path.name.startswith("gog-")
