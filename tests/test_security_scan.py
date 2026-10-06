from pathlib import Path
import importlib.util

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "security_scan.py"
spec = importlib.util.spec_from_file_location("security_scan", MODULE)
security_scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security_scan)

def titles(text):
    return {item["title"] for item in security_scan.scan_text(text)}

def test_safe_code_has_no_security_finding():
    assert not titles("def add(a, b):\n    return a + b")

def test_eval_is_detected():
    assert "Execução dinâmica potencialmente perigosa em Python" in titles("result = eval(user_input)")

def test_hardcoded_key_pattern_is_detected():
    assert "Possível segredo hardcoded" in titles('api_key = "abcdefghijklmnop123456"')

def test_fstring_double_braces_are_not_a_security_finding():
    assert not titles('message = f"{{value}}"')
