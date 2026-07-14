"""Tests for the compatibility list-demos command."""

from typer.testing import CliRunner

from lappa.cli import app


def test_list_demos_empty(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["list-demos", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "No packages directory" in result.output


def test_list_demos_with_packages(tmp_path):
    demo_dir = tmp_path / "packages" / "my_robot" / "demo"
    demo_dir.mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(app, ["list-demos", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "my_robot" in result.output
    assert str(demo_dir) in result.output
