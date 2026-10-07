import tempfile, os
from scripts.policy import load_policy

def test_policy_loads_core_values():
    data="version: 1\nreview:\n  min_score: 7\n  fail_on_high_risk: true\npull_request:\n  event: REQUEST_CHANGES\n"
    with tempfile.NamedTemporaryFile("w",delete=False,encoding="utf-8") as f:
        f.write(data); path=f.name
    try:
        p=load_policy(path)
        assert p["review"]["min_score"] == 7
        assert p["review"]["fail_on_high_risk"] is True
        assert p["pull_request"]["event"] == "REQUEST_CHANGES"
    finally:
        os.unlink(path)

def test_missing_policy_is_safe():
    p=load_policy("/tmp/does-not-exist-ai-devops.yml")
    assert p["review"]["min_score"] == 0
    assert p["review"]["fail_on_high_risk"] is False
