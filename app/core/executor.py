from __future__ import annotations

from app.models.execution import ExecutionResult, StepExecutionResult
from app.models.plan import AgentPlan
from app.tools.registry import ToolRegistry


class Executor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(self, plan: AgentPlan) -> ExecutionResult:
        step_results: list[StepExecutionResult] = []
        errors: list[str] = []

        for step in plan.steps:

            # Step does not have a tool yet.
            # For now, we simply skip it.
            if step.tool_name is None:
                step_results.append(
                    StepExecutionResult(
                        step_id=step.id,
                        success=False,
                        tool_result=None,
                        error="Step skipped because no tool is configured.",
                    )
                )
                errors.append(f"Step '{step.id}' has no configured tool.")
                continue

            # Find the required tool in the registry.
            try:
                tool = self.registry.get(step.tool_name)

            except KeyError as exc:
                step_results.append(
                    StepExecutionResult(
                        step_id=step.id,
                        success=False,
                        tool_result=None,
                        error=str(exc),
                    )
                )

                errors.append(str(exc))
                continue

            # Execute the tool.
            try:
                tool_result = await tool.execute(
                    **(step.tool_input or {})
                )

            except Exception as exc:
                error_message = (
                    f"Tool '{step.tool_name}' execution failed: {exc}"
                )

                step_results.append(
                    StepExecutionResult(
                        step_id=step.id,
                        success=False,
                        tool_result=None,
                        error=error_message,
                    )
                )

                errors.append(error_message)
                continue

            # Store the tool result.
            step_results.append(
                StepExecutionResult(
                    step_id=step.id,
                    success=tool_result.success,
                    tool_result=tool_result,
                    error=tool_result.error,
                )
            )

            # Stop execution if the tool itself reports failure.
            if not tool_result.success:
                errors.append(
                    tool_result.error or f"Tool '{step.tool_name}' failed."
                )

        # Preserve every step outcome and aggregate independent failures.
        return ExecutionResult(
            success=not errors,
            step_results=step_results,
            error="; ".join(errors) if errors else None,
        )
