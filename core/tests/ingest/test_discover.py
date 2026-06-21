"""Unit tests for source-agnostic file discovery (ARCHITECTURE.md §8).

discover(root) is the front of the §8 ingest pipeline: it returns every regular file under
`root` as a deterministic, sorted tuple of DiscoveredFile (relative POSIX paths), honoring a
root-level .gitignore + .brainignore, always excluding the VCS / brain-output dirs, source-agnostic
about other dotfile dirs, and never following symlinks (no escape outside root, no cycles).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest.discover import DiscoveredFile, discover

pytestmark = pytest.mark.unit


def _paths(root: Path) -> set[str]:
    return {df.path for df in discover(root)}


def test_discover_finds_regular_files(tmp_path: Path) -> None:
    # spec(§8): source-agnostic discovery returns every regular file under root.
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("y")
    assert _paths(tmp_path) == {"a.py", "sub/b.md"}


def test_discover_returns_discovered_file_tuple(tmp_path: Path) -> None:
    # spec(§8): the public shape is a tuple of DiscoveredFile carrying a relative POSIX path.
    (tmp_path / "a.py").write_text("x")
    out = discover(tmp_path)
    assert isinstance(out, tuple)
    assert all(isinstance(df, DiscoveredFile) for df in out)
    assert out[0].path == "a.py"


def test_discover_honors_gitignore(tmp_path: Path) -> None:
    # spec(§8): a path matching a root .gitignore pattern is excluded.
    (tmp_path / ".gitignore").write_text("ignored.py\n*.log\n")
    (tmp_path / "keep.py").write_text("x")
    (tmp_path / "ignored.py").write_text("x")
    (tmp_path / "debug.log").write_text("x")
    paths = _paths(tmp_path)
    assert "keep.py" in paths
    assert "ignored.py" not in paths
    assert "debug.log" not in paths


def test_discover_honors_brainignore(tmp_path: Path) -> None:
    # spec(§8): a root .brainignore pattern is honored AND combines with .gitignore.
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / ".brainignore").write_text("secret/\n")
    (tmp_path / "app.py").write_text("x")
    (tmp_path / "debug.log").write_text("x")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "k.txt").write_text("x")
    paths = _paths(tmp_path)
    assert "app.py" in paths
    assert "debug.log" not in paths  # from .gitignore
    assert "secret/k.txt" not in paths  # from .brainignore


def test_discover_always_excludes_git_and_brain_dirs(tmp_path: Path) -> None:
    # spec(§8): .git/ and the brain's own .project-brain/ are always excluded (no ignore file).
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    (tmp_path / ".project-brain").mkdir()
    (tmp_path / ".project-brain" / "index.lance").write_text("x")
    (tmp_path / "app.py").write_text("x")
    paths = _paths(tmp_path)
    assert paths == {"app.py"}


def test_discover_includes_github_dir(tmp_path: Path) -> None:
    # spec(§8): source-agnostic — a dotfile dir like .github/ is NOT blanket-excluded.
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("x")
    assert ".github/workflows/ci.yml" in _paths(tmp_path)


def test_discover_deterministic_sorted_order(tmp_path: Path) -> None:
    # spec(§8): determinism posture — two calls return byte-identical, sorted tuples.
    for name in ("c.py", "a.py", "b.py"):
        (tmp_path / name).write_text("x")
    (tmp_path / "z").mkdir()
    (tmp_path / "z" / "y.py").write_text("x")
    first = discover(tmp_path)
    second = discover(tmp_path)
    assert first == second
    paths = [df.path for df in first]
    assert paths == sorted(paths)


def test_discover_does_not_follow_symlinks(tmp_path: Path) -> None:
    # spec(§8): containment — a symlink (esp. to a dir outside root) is not traversed.
    outside = tmp_path / "outside_target"
    outside.mkdir()
    (outside / "leak.py").write_text("secret")
    root = tmp_path / "root"
    root.mkdir()
    (root / "app.py").write_text("x")
    (root / "link_to_outside").symlink_to(outside, target_is_directory=True)
    paths = _paths(root)
    assert "app.py" in paths
    assert not any("leak" in p for p in paths)
    assert "link_to_outside" not in paths


def test_discover_skips_symlinked_file(tmp_path: Path) -> None:
    # spec(§8): containment also covers a symlinked FILE (the 2nd is_symlink guard), not just dirs.
    target = tmp_path / "target.py"
    target.write_text("secret")
    root = tmp_path / "root"
    root.mkdir()
    (root / "app.py").write_text("x")
    (root / "link.py").symlink_to(target)
    paths = _paths(root)
    assert paths == {"app.py"}


def test_discover_honors_extra_ignores(tmp_path: Path) -> None:
    # spec(§8): caller-supplied gitwildmatch patterns layer on top of the root ignore files.
    (tmp_path / "keep.py").write_text("x")
    (tmp_path / "drop.secret").write_text("x")
    paths = {df.path for df in discover(tmp_path, extra_ignores=["*.secret"])}
    assert "keep.py" in paths
    assert "drop.secret" not in paths


def test_discover_empty_dir_returns_empty_tuple(tmp_path: Path) -> None:
    # spec(§8): an existing-but-empty root yields () (a valid empty repo, not an error).
    assert discover(tmp_path) == ()


def test_discover_raises_on_nonexistent_root(tmp_path: Path) -> None:
    # spec(§8): a non-existent root is a caller error — fail loud, don't masquerade as empty.
    with pytest.raises(NotADirectoryError):
        discover(tmp_path / "does_not_exist")


def test_discover_raises_on_file_root(tmp_path: Path) -> None:
    # spec(§8): a file passed as root is a caller error — fail loud.
    f = tmp_path / "a_file.py"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        discover(f)


def test_discover_tolerates_non_utf8_ignore_file(tmp_path: Path) -> None:
    # spec(§8): a binary / non-UTF-8 .gitignore must not crash discovery (errors="replace").
    (tmp_path / ".gitignore").write_bytes(b"keep_me\xff\xfe not utf-8\n*.log\n")
    (tmp_path / "app.py").write_text("x")
    (tmp_path / "debug.log").write_text("x")
    paths = _paths(tmp_path)  # must not raise UnicodeDecodeError
    assert "app.py" in paths
    assert "debug.log" not in paths  # the valid pattern past the bad bytes still applies


def test_discover_skips_oversized_ignore_file(tmp_path: Path) -> None:
    # spec(§8): an oversized ignore file is skipped (DoS guard), not loaded into memory.
    big = "x" * (1_048_576 + 1)  # one byte over IGNORE_FILE_MAX_BYTES
    (tmp_path / ".gitignore").write_text(big + "\n")
    (tmp_path / "app.py").write_text("x")
    assert discover(tmp_path) is not None  # must not raise/OOM
    assert "app.py" in _paths(tmp_path)
