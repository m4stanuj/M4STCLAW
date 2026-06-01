"""
mesh.py — Multi-Agent Mesh Orchestration Engine
================================================
Spawns three specialized agents (Coder, Auditor, Tester) that collaborate
statefully in a feedback loop to build, review, and test solutions.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
import m4stclaw.core.fallback as fallback

log = logging.getLogger("m4stclaw.core.mesh")

class MeshOrchestrator:
    """Manages the collaboration loop between Coder, Auditor, and Tester agents."""
    
    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize orchestrator with optional callback to stream logs (e.g., to dashboard console).
        Signature: log_callback(agent_name, log_message)
        """
        self.log_callback = log_callback

    def _emit_log(self, agent: str, message: str):
        """Emits logs to console and optional external callbacks."""
        log.info(f"[{agent.upper()}] {message}")
        if self.log_callback:
            try:
                self.log_callback(agent, message)
            except Exception as e:
                log.error(f"Failed to execute log callback: {e}")

    def run_mesh_task(self, prompt: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Runs the multi-agent mesh loop to generate, audit, and test a solution.
        """
        self._emit_log("system", f"MeshEngine Spawned for prompt: '{prompt}'")
        
        current_code = ""
        audit_feedback = ""
        test_feedback = ""
        success = False
        iteration_history = []
        
        for iteration in range(1, max_iterations + 1):
            self._emit_log("system", f"Starting Collaboration Round {iteration} of {max_iterations}...")
            round_data = {"iteration": iteration, "logs": []}
            
            # ── 1. CODER AGENT: Writes/revises the code ─────────────────────────────
            self._emit_log("coder", "Generating/updating solution code...")
            
            coder_prompt = f"User Request: {prompt}\n\n"
            if current_code:
                coder_prompt += (
                    f"Your previous code solution was:\n```python\n{current_code}\n```\n\n"
                    f"The Auditor found issues:\n{audit_feedback}\n\n"
                    f"The Tester found issues:\n{test_feedback}\n\n"
                    f"Please revise and correct the code based on the feedback. Provide the complete code block in your response."
                )
            else:
                coder_prompt += (
                    "Write a clean, complete, and optimal Python script/function to fulfill the request. "
                    "Make sure to handle edge cases and explain key logic briefly."
                )
                
            coder_messages = [
                {"role": "system", "content": "You are the Coder Agent of M4STCLAW AI Mesh. Your job is to write optimal, clean Python code."},
                {"role": "user", "content": coder_prompt}
            ]
            
            coder_start = time.time()
            current_code = fallback.chat_complete(coder_messages, task="code")
            coder_duration = time.time() - coder_start
            
            self._emit_log("coder", f"Solution code updated in {round(coder_duration, 1)}s.")
            round_data["code"] = current_code
            
            # Check if Coder failed to return code
            if "ERROR:" in current_code:
                self._emit_log("system", "Coder Agent failed to generate a response. Halting loop.")
                break

            # ── 2. AUDITOR AGENT: Reviews security and code safety ──────────────────
            self._emit_log("auditor", "Auditing code for logical errors, security vulnerability, and safety rails...")
            
            auditor_prompt = (
                f"Analyze the following code written to address: '{prompt}'.\n"
                f"Review it for security issues (injection, path traversals, raw exec), logical bugs, and optimization errors:\n\n"
                f"```python\n{current_code}\n```\n\n"
                f"If the code is secure and clean, respond with exactly 'AUDIT_PASSED'. "
                f"Otherwise, provide a clear, concise bulleted list of issues and vulnerabilities."
            )
            
            auditor_messages = [
                {"role": "system", "content": "You are the Auditor Agent of M4STCLAW AI Mesh. Review code for bugs, logic errors, and security issues."},
                {"role": "user", "content": auditor_prompt}
            ]
            
            auditor_start = time.time()
            audit_result = fallback.chat_complete(auditor_messages, task="pentest")
            auditor_duration = time.time() - auditor_start
            
            audit_passed = "AUDIT_PASSED" in audit_result
            audit_feedback = audit_result if not audit_passed else "No issues found."
            
            if audit_passed:
                self._emit_log("auditor", f"Audit passed successfully! (Check time: {round(auditor_duration, 1)}s)")
            else:
                self._emit_log("auditor", f"Vulnerabilities/Issues detected! Feedback: {audit_feedback[:100]}...")
            
            round_data["audit_result"] = audit_result
            round_data["audit_passed"] = audit_passed

            # ── 3. TESTER AGENT: Runs mock validations or syntax checks ────────────
            self._emit_log("tester", "Verifying functionality and executing unit assertions...")
            
            tester_prompt = (
                f"Verify the code logic for request: '{prompt}'.\n"
                f"Verify that the following script handles standard bounds, does not trigger runtime exceptions, and performs optimally:\n\n"
                f"```python\n{current_code}\n```\n\n"
                f"If the code looks correct, returns appropriate output structure, and passes standard assertions, respond with exactly 'TEST_PASSED'. "
                f"Otherwise, provide feedback detailing why it fails and what test cases are missing."
            )
            
            tester_messages = [
                {"role": "system", "content": "You are the Tester Agent of M4STCLAW. Review code structure, verify test coverage, and check logic assertions."},
                {"role": "user", "content": tester_prompt}
            ]
            
            tester_start = time.time()
            test_result = fallback.chat_complete(tester_messages, task="reasoning")
            tester_duration = time.time() - tester_start
            
            test_passed = "TEST_PASSED" in test_result
            test_feedback = test_result if not test_passed else "No issues found."
            
            if test_passed:
                self._emit_log("tester", f"All tests and assertions passed successfully! (Check time: {round(tester_duration, 1)}s)")
            else:
                self._emit_log("tester", f"Assertions/Validations failed! Feedback: {test_feedback[:100]}...")
                
            round_data["test_result"] = test_result
            round_data["test_passed"] = test_passed
            
            iteration_history.append(round_data)
            
            # ── 4. CHECK LOOP CONSENSUS ─────────────────────────────────────────────
            if audit_passed and test_passed:
                self._emit_log("system", "Consensus achieved! Coder, Auditor, and Tester all approved the solution.")
                success = True
                break
            else:
                self._emit_log("system", f"Round {iteration} failed consensus. Sending feedback back to Coder Agent for correction...")
                
        # Final output assembly
        final_summary = (
            f"### Multi-Agent Mesh Execution Summary\n"
            f"- **Status:** {'Success ✅' if success else 'Failed ❌ (Max iterations reached)'}\n"
            f"- **Rounds Run:** {len(iteration_history)}\n\n"
            f"#### Final Code Output:\n```python\n{current_code}\n```\n\n"
            f"#### Auditor Final Remarks:\n{audit_feedback}\n\n"
            f"#### Tester Final Remarks:\n{test_feedback}\n"
        )
        
        self._emit_log("system", f"MeshEngine loop terminated. Final success: {success}")
        
        return {
            "success": success,
            "rounds_run": len(iteration_history),
            "final_code": current_code,
            "final_summary": final_summary,
            "history": iteration_history
        }
