"""
Unit tests for Deno runtime implementation.

Following TDD methodology - RED phase: Writing failing tests first.
Phase 7.2.1: Deno Runtime Initialization Test
"""

import uuid
import pytest
from datetime import datetime, timezone


def test_deno_runtime_initialization():
    """
    Test DenoRuntime can be initialized and configured.
    
    RED Phase: This test will fail - DenoRuntime doesn't exist yet.
    GREEN Phase: Implement DenoRuntime class to make this pass.
    REFACTOR Phase: Clean up runtime code if needed.
    """
    # Import will fail - runtime doesn't exist yet
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize Deno runtime
    runtime = DenoRuntime()
    
    # Verify runtime properties
    assert runtime.name == "deno"
    assert runtime.version is not None
    assert runtime.is_available() is True
    assert runtime.supports_typescript() is True
    assert runtime.supports_javascript() is True


def test_deno_runtime_code_execution():
    """
    Test DenoRuntime can execute TypeScript/JavaScript code.
    
    RED Phase: This test will fail - execute() method doesn't exist yet.
    GREEN Phase: Add execute() method to DenoRuntime.
    REFACTOR Phase: Optimize execution if needed.
    """
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize runtime
    runtime = DenoRuntime()
    
    # Simple JavaScript code
    js_code = '''
    console.log("Hello from Deno!");
    return { message: "success", timestamp: new Date().toISOString() };
    '''
    
    # Execute code
    result = runtime.execute(js_code)
    
    # Verify execution result
    assert result is not None
    assert result.success is True
    assert result.return_value is not None
    assert result.return_value["message"] == "success"
    assert "timestamp" in result.return_value
    assert result.error_message is None
    assert result.execution_time_ms > 0


def test_deno_runtime_typescript_execution():
    """
    Test DenoRuntime can execute TypeScript code with type checking.
    
    This verifies TypeScript compilation and execution.
    """
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize runtime
    runtime = DenoRuntime()
    
    # TypeScript code with interfaces
    ts_code = '''
    interface User {
        id: number;
        name: string;
        email: string;
    }
    
    const user: User = {
        id: 1,
        name: "Test User",
        email: "test@example.com"
    };
    
    console.log(`User: ${user.name} <${user.email}>`);
    return { user, processed: true };
    '''
    
    # Execute TypeScript code
    result = runtime.execute(ts_code)
    
    # Verify execution result
    assert result.success is True
    assert result.return_value["user"]["name"] == "Test User"
    assert result.return_value["user"]["email"] == "test@example.com"
    assert result.return_value["processed"] is True


def test_deno_runtime_error_handling():
    """
    Test DenoRuntime properly handles code execution errors.
    
    This verifies error capture and reporting.
    """
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize runtime
    runtime = DenoRuntime()
    
    # Code with syntax error
    bad_code = '''
    console.log("This will fail");
    throw new Error("Intentional test error");
    return { should_not_reach: true };
    '''
    
    # Execute bad code
    result = runtime.execute(bad_code)
    
    # Verify error handling
    assert result.success is False
    assert result.error_message is not None
    assert "Intentional test error" in result.error_message
    assert result.return_value is None
    assert result.execution_time_ms > 0


def test_deno_runtime_timeout_handling():
    """
    Test DenoRuntime handles execution timeouts properly.
    
    This prevents runaway code from blocking the system.
    """
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize runtime with short timeout
    runtime = DenoRuntime(timeout_ms=100)
    
    # Code that runs longer than timeout
    timeout_code = '''
    // Sleep for 1 second (longer than 100ms timeout)
    await new Promise(resolve => setTimeout(resolve, 1000));
    return { completed: true };
    '''
    
    # Execute code that should timeout
    result = runtime.execute(timeout_code)
    
    # Verify timeout handling
    assert result.success is False
    assert result.error_message is not None
    assert "timeout" in result.error_message.lower()
    assert result.execution_time_ms >= 100  # Should be at least the timeout duration


def test_deno_runtime_memory_isolation():
    """
    Test DenoRuntime isolates execution contexts between runs.
    
    This ensures functions don't interfere with each other.
    """
    from shared.runtime.deno_runtime import DenoRuntime
    
    # Initialize runtime
    runtime = DenoRuntime()
    
    # First execution sets a variable
    first_code = '''
    let globalVar = "first execution";
    return { value: globalVar };
    '''
    
    result1 = runtime.execute(first_code)
    assert result1.success is True
    assert result1.return_value["value"] == "first execution"
    
    # Second execution should not see the variable
    second_code = '''
    try {
        return { value: globalVar, found: true };
    } catch (error) {
        return { value: null, found: false, error: error.message };
    }
    '''
    
    result2 = runtime.execute(second_code)
    assert result2.success is True
    assert result2.return_value["found"] is False
    assert result2.return_value["value"] is None