from pathlib import Path

import pytest

import organizer


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Point organizer's move log at a fresh temp file for each test.

    This keeps tests from ever touching the real moves.json.
    """
    monkeypatch.setattr(organizer, "moves_file", tmp_path / "moves.json")
    return tmp_path


def make_file(root, name, content="x"):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def id_for(moves, filename):
    """Look up a move id by the source file's name (iteration order is not
    guaranteed, so never hard-code ids in tests)."""
    for m in moves:
        if Path(m["source"]).name == filename:
            return m["id"]
    raise AssertionError(f"no move recorded for {filename}")


# ---------------------------------------------------------------------------
# extract_title / sanitize_folder_name
# ---------------------------------------------------------------------------

def test_extract_title_series():
    assert (
        organizer.extract_title("06 - Sakamoto Days [720p] [Sub] @Animes_War.mkv")
        == "Sakamoto Days"
    )
    assert (
        organizer.extract_title("Bleach - 001 [720p] [Dual] @Anime_Gallery.mkv")
        == "Bleach"
    )


def test_sanitize_folder_name():
    assert organizer.sanitize_folder_name('a<b>c:d"e/f\\g|h?i*j') == "abcdefghij"
    assert (
        organizer.sanitize_folder_name("Trailing dots and spaces ... ")
        == "Trailing dots and spaces"
    )


# ---------------------------------------------------------------------------
# organize
# ---------------------------------------------------------------------------

def test_organize_sorts_by_extension(isolated):
    make_file(isolated, "script.py")
    make_file(isolated, "photo.png")
    make_file(isolated, "song.mp3")
    make_file(isolated, "archive.zip")
    make_file(isolated, "doc.pdf")
    make_file(isolated, "setup.exe")
    make_file(isolated, "mystery.xyz")

    organizer.organize_files(str(isolated))

    assert (isolated / "Code" / "script.py").exists()
    assert (isolated / "Images" / "photo.png").exists()
    assert (isolated / "Audio" / "song.mp3").exists()
    assert (isolated / "Archive" / "archive.zip").exists()
    assert (isolated / "Documents" / "doc.pdf").exists()
    assert (isolated / "Programs" / "setup.exe").exists()
    assert (isolated / "Unknown" / "mystery.xyz").exists()


def test_organize_video_series_grouping(isolated):
    make_file(isolated, "06 - Sakamoto Days [720p] [Sub] @Animes_War.mkv")
    make_file(isolated, "07 - Sakamoto Days [720p] [Sub] @Animes_War.mkv")
    make_file(isolated, "Bleach - 001 [720p] [Dual] @Anime_Gallery.mkv")

    organizer.organize_files(str(isolated))

    assert (
        isolated / "Sakamoto Days" / "06 - Sakamoto Days [720p] [Sub] @Animes_War.mkv"
    ).exists()
    assert (
        isolated / "Sakamoto Days" / "07 - Sakamoto Days [720p] [Sub] @Animes_War.mkv"
    ).exists()
    assert (
        isolated / "Bleach" / "Bleach - 001 [720p] [Dual] @Anime_Gallery.mkv"
    ).exists()


def test_organize_logs_moves(isolated):
    make_file(isolated, "script.py")

    organizer.organize_files(str(isolated))

    moves = organizer.load_moves()
    assert len(moves) == 1
    assert moves[0]["reverted"] is False
    assert moves[0]["source"] == str(isolated / "script.py")
    assert moves[0]["destination"] == str(isolated / "Code" / "script.py")


def test_duplicate_destination_skipped(isolated):
    (isolated / "Code").mkdir(parents=True)
    (isolated / "Code" / "script.py").write_text("existing", encoding="utf-8")
    (isolated / "script.py").write_text("new", encoding="utf-8")

    organizer.organize_files(str(isolated))

    # The existing destination file must not be overwritten.
    assert (isolated / "Code" / "script.py").read_text(encoding="utf-8") == "existing"
    assert (isolated / "script.py").exists()
    # Nothing was moved, so nothing is logged.
    assert organizer.load_moves() == []


# ---------------------------------------------------------------------------
# revert
# ---------------------------------------------------------------------------

def test_revert_all(isolated):
    make_file(isolated, "script.py")
    make_file(isolated, "photo.png")
    organizer.organize_files(str(isolated))

    organizer.revert_moves(organizer.load_moves())

    assert (isolated / "script.py").exists()
    assert (isolated / "photo.png").exists()
    assert not (isolated / "Code").exists()
    assert not (isolated / "Images").exists()
    assert all(m["reverted"] for m in organizer.load_moves())


def test_revert_file_single(isolated):
    make_file(isolated, "a.py")
    make_file(isolated, "b.py")
    organizer.organize_files(str(isolated))

    a_id = id_for(organizer.load_moves(), "a.py")
    organizer.revert_file(a_id, organizer.load_moves())

    assert (isolated / "a.py").exists()  # reverted
    assert (isolated / "Code" / "b.py").exists()  # still moved


def test_revert_file_unknown_id(isolated):
    make_file(isolated, "a.py")
    organizer.organize_files(str(isolated))

    # Must not raise.
    organizer.revert_file(999, organizer.load_moves())


def test_revert_file_already_reverted(isolated):
    make_file(isolated, "a.py")
    organizer.organize_files(str(isolated))
    organizer.revert_file(1, organizer.load_moves())

    # Second revert is a no-op.
    organizer.revert_file(1, organizer.load_moves())
    assert organizer.load_moves()[0]["reverted"] is True


def test_organize_revert_cycle(isolated):
    name = "script.py"
    make_file(isolated, name)

    # organize -> False
    organizer.organize_files(str(isolated))
    assert organizer.load_moves()[0]["reverted"] is False
    assert (isolated / "Code" / name).exists()

    # revert -> True
    organizer.revert_file(1, organizer.load_moves())
    assert organizer.load_moves()[0]["reverted"] is True
    assert (isolated / name).exists()

    # organize again -> reuses the entry, resets to False, no duplicates
    organizer.organize_files(str(isolated))
    moves = organizer.load_moves()
    assert len(moves) == 1
    assert moves[0]["reverted"] is False
    assert (isolated / "Code" / name).exists()

    # revert again -> True
    organizer.revert_file(1, organizer.load_moves())
    assert organizer.load_moves()[0]["reverted"] is True
    assert (isolated / name).exists()


# ---------------------------------------------------------------------------
# history / clear
# ---------------------------------------------------------------------------

def test_clear_history(isolated):
    make_file(isolated, "a.py")
    organizer.organize_files(str(isolated))
    assert organizer.load_moves()

    organizer.clear_history()
    assert organizer.load_moves() == []


def test_history_prints(capsys, isolated):
    make_file(isolated, "a.py")
    organizer.organize_files(str(isolated))

    organizer.history(organizer.load_moves())
    out = capsys.readouterr().out
    assert "a.py" in out
