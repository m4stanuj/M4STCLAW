import pytest
from unittest.mock import patch
from m4stclaw.core.mesh import MeshOrchestrator

def mock_chat_complete(messages, task):
    # Simulate Coder Agent output
    if task == "code":
        return "def hello():\n    return 'world'"
    # Simulate Auditor Agent output
    elif task == "pentest":
        return "AUDIT_PASSED"
    # Simulate Tester Agent output
    elif task == "reasoning":
        return "TEST_PASSED"
    return "MOCK_RESPONSE"

def test_mesh_orchestrator_success():
    """Verifies that the mesh engine achieves success on first round when agents agree."""
    with patch("m4stclaw.core.fallback.chat_complete", side_effect=mock_chat_complete):
        orchestrator = MeshOrchestrator()
        result = orchestrator.run_mesh_task("Write a function that returns world", max_iterations=2)
        
        assert result["success"] is True
        assert result["rounds_run"] == 1
        assert "hello()" in result["final_code"]
        assert "Success ✅" in result["final_summary"]

def test_mesh_orchestrator_audit_feedback_loop():
    """Verifies that coder revises the solution when auditor detects issues, succeeding in round 2."""
    call_count = 0
    
    def mock_chat_complete_loop(messages, task):
        nonlocal call_count
        if task == "code":
            call_count += 1
            if call_count == 1:
                return "def insecure():\n    eval('1+1')"
            return "def secure():\n    pass"
        elif task == "pentest":
            if call_count == 1:
                return "Use of eval() detected, please remove."
            return "AUDIT_PASSED"
        elif task == "reasoning":
            return "TEST_PASSED"
        return "MOCK_RESPONSE"

    with patch("m4stclaw.core.fallback.chat_complete", side_effect=mock_chat_complete_loop):
        orchestrator = MeshOrchestrator()
        result = orchestrator.run_mesh_task("Write secure function", max_iterations=3)
        
        assert result["success"] is True
        assert result["rounds_run"] == 2
        assert "secure()" in result["final_code"]
        assert "No issues found." in result["final_summary"]
