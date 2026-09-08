import httpx
import pytest
from scripts.soak_http import require_rpc_success


@pytest.mark.parametrize("payload", [
    '{"id":1,"error":{"message":"failed"}}',
    '{"id":1,"result":{"isError":true}}',
    '{"id":1,"result":{"structuredContent":{"success":false}}}',
    '{"method":"notifications/progress","params":{}}',
])
def test_soak_cannot_treat_http_200_as_success(payload):
    response = httpx.Response(200, text="data: "+payload+"\n\n",
                              request=httpx.Request("POST","http://localhost/mcp"))
    with pytest.raises(RuntimeError):
        require_rpc_success(response)


def test_short_soak_never_passes():
    from scripts.analyze_soak import analyze
    assert not analyze([{"elapsed":600}])["passed"]


@pytest.mark.parametrize("growth,passed", [(0,True),(9,True),(11,False)])
def test_post_warmup_rss_growth_gate(growth,passed):
    from scripts.analyze_soak import analyze
    samples = [{"elapsed":minute*60,"sessions":0,"tasks":7,"threads":5,"file_descriptors":10,
                "rss_bytes":(100+growth*minute/60)*1048576} for minute in range(121)]
    assert analyze(samples)["passed"] is passed


def test_retained_sessions_fail_even_if_rss_is_flat():
    from scripts.analyze_soak import analyze
    samples = [{"elapsed":minute*60,"sessions":1,"tasks":7,"threads":5,"file_descriptors":10,
                "rss_bytes":100*1048576} for minute in range(121)]
    assert "Sessions retained after cleanup" in analyze(samples)["reasons"]
