"""The GARMIN_TOKEN blob must survive an export → materialize round-trip —
this is the path the headless sync + self-refresh depends on."""

from __future__ import annotations

from paceforge import actions


def test_token_blob_round_trips(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "oauth1_token.json").write_text('{"a":1}')
    (src / "oauth2_token.json").write_text('{"b":2}')

    blob = actions._export_token(src)

    dst = tmp_path / "dst"
    monkeypatch.setenv("GARMIN_TOKEN", blob)
    actions._materialize_token(dst)

    assert (dst / "oauth1_token.json").read_text() == '{"a":1}'
    assert (dst / "oauth2_token.json").read_text() == '{"b":2}'
