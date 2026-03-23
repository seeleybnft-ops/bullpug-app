"""
Test that ensure_sufficient_sol_for_trade is called before buy execution paths.
This is a structural/integration test — it verifies the auto-burn function is
correctly wired into both the signal-based and runner-based buy paths.
"""
import ast
import os

AI_TRADER_PATH = os.path.join(os.path.dirname(__file__), "..", "routers", "ai_trader.py")


def get_function_calls_in_function(filepath: str, target_function: str):
    """Parse the AST and return all function call names within target_function."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == target_function:
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            calls.append(child.func.attr)
                return calls
    return []


def test_auto_burn_integrated_in_scan_and_execute():
    """ensure_sufficient_sol_for_trade must be called inside auto_trade_scan_and_execute."""
    calls = get_function_calls_in_function(AI_TRADER_PATH, "auto_trade_scan_and_execute")
    assert "ensure_sufficient_sol_for_trade" in calls, (
        "ensure_sufficient_sol_for_trade is NOT called inside auto_trade_scan_and_execute. "
        "Auto-burn before buys is not integrated."
    )


def test_auto_burn_called_before_execute_auto_trade():
    """ensure_sufficient_sol_for_trade must appear before execute_auto_trade in the source."""
    with open(AI_TRADER_PATH) as f:
        source = f.read()

    # Check signal-based buy path
    signal_burn = source.find("Auto-burn empty accounts to reclaim SOL before buying")
    signal_exec = source.find("Executing auto-trade via custodial wallet")
    assert signal_burn != -1, "Auto-burn comment not found in signal buy path"
    assert signal_burn < signal_exec, "Auto-burn must happen BEFORE trade execution in signal path"

    # Check runner-based buy path
    runner_burn = source.find("Auto-burn empty accounts to reclaim SOL before runner buy")
    runner_exec = source.find("Executing runner trade via custodial wallet")
    assert runner_burn != -1, "Auto-burn comment not found in runner buy path"
    assert runner_burn < runner_exec, "Auto-burn must happen BEFORE trade execution in runner path"


if __name__ == "__main__":
    test_auto_burn_integrated_in_scan_and_execute()
    print("PASS: ensure_sufficient_sol_for_trade found in scan_and_execute")

    test_auto_burn_called_before_execute_auto_trade()
    print("PASS: Auto-burn called before execute_auto_trade in both buy paths")

    print("\nAll auto-burn integration tests passed!")
