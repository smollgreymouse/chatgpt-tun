from chatgpt_tun import doctor

def test_doctor_reports_missing_ngrok_without_mutating(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATGPT_TUN_HOME", str(tmp_path))
    monkeypatch.setattr(doctor, "ngrok_version", lambda _: (_ for _ in ()).throw(doctor.NgrokError("missing")))
    result = doctor.diagnose()
    assert result["ok"] is False
    assert any(x["name"] == "ngrok" and not x["ok"] for x in result["checks"])
    assert not (tmp_path / "registry.json").exists()

def test_doctor_machine_readable(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CHATGPT_TUN_HOME", str(tmp_path))
    code = doctor.print_diagnostics(json_mode=True)
    import json
    d = json.loads(capsys.readouterr().out)
    assert d["platform"]
    assert isinstance(d["checks"], list)
    assert code in (0, 2)
