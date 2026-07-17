import json

from splitflap_cad.__main__ import main


def test_list_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["splitflap_cad", "list", "--json"])
    main()
    data = json.loads(capsys.readouterr().out)
    assert "assembly" in data["models"]
    assert set(data["printable"]) <= set(data["models"]) | set(data["printable"])
    assert all(isinstance(v, str) for v in data["src_to_model"].values())
