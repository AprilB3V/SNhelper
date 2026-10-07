from snhelper.memory import SQLiteMemoryStore
from snhelper.models import Intent
from snhelper.orchestrator import Orchestrator


def test_router_supports_collaboration():
    orchestrator = Orchestrator(SQLiteMemoryStore(":memory:"))
    result = orchestrator.handle("我想记录创业灵感，并拆解明天开始的第一步")
    assert result.route.primary in {Intent.ARCHIVE, Intent.EXECUTE}
    assert len(result.results) >= 2


def test_archivist_persists_and_searches():
    store = SQLiteMemoryStore(":memory:")
    orchestrator = Orchestrator(store)
    orchestrator.handle("记录一个关于量子计算的灵感")
    result = orchestrator.search_memory("量子计算")
    assert "量子计算" in result.content


def test_unknown_input_has_actionable_fallback():
    orchestrator = Orchestrator(SQLiteMemoryStore(":memory:"))
    result = orchestrator.handle("今天状态一般")
    assert result.results[0].agent == "enforcer"
    assert "10 分钟" in result.results[0].content

