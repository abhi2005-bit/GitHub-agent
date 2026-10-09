from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agent.planner import Planner
from app.agent.understander import Understander
from app.core.executor import Executor
from app.core.policy import PolicyEngine
from app.core.project_context import ProjectContext
from app.models.agent import AgentMessage, AgentRun, AgentState


class AgentRunner:
    """
    Coordinates the lifecycle of an agent run.
    """

    def __init__(
        self,
        understander: Understander,
        planner: Planner,
        policy_engine: PolicyEngine,
        executor: Executor,
        project_context: ProjectContext,
    ) -> None:
        self.understander = understander
        self.planner = planner
        self.policy_engine = policy_engine
        self.executor = executor
        self.project_context = project_context

    async def run(
        self,
        goal: str,
        project_id: int | None = None,
    ) -> AgentRun:
        run = AgentRun(
            goal=goal,
            project_id=project_id,
        )

        try:
            # Resolve the selected project, if provided.
            project = None

            if project_id is not None:
                project = self.project_context.get_project(project_id)

            # Agent starts thinking.
            self._update_state(run, AgentState.THINKING)

            run.messages.append(
                AgentMessage(
                    role="user",
                    content=goal,
                )
            )

            run.messages.append(
                AgentMessage(
                    role="system",
                    content="Agent run started.",
                )
            )

            # Understand the user's goal.
            understanding = self.understander.understand(run.goal)

            run.messages.append(
                AgentMessage(
                    role="agent",
                    content=f"Goal understood as: {understanding.intent.value}.",
                )
            )

            # Create a plan using the understanding and selected project.
            plan = self.planner.create_plan(
                understanding=understanding,
                project=project,
            )

            run.messages.append(
                AgentMessage(
                    role="agent",
                    content=f"Plan created with {len(plan.steps)} step(s).",
                )
            )

            # Evaluate the plan against policy.
            policy_decision = self.policy_engine.evaluate(plan)

            if not policy_decision.allowed:
                self._update_state(run, AgentState.FAILED)
                run.error = policy_decision.reason

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content=(
                            "Agent execution blocked by policy: "
                            f"{policy_decision.reason}"
                        ),
                    )
                )

                return run

            # Agent starts acting.
            self._update_state(run, AgentState.ACTING)

            # Execute the plan.
            result = await self.executor.execute(plan)

            # Record the results returned by each executed tool.
            for step_result in result.step_results:
                if step_result.tool_result is None:
                    continue

                tool_result_data = {
                    "success": step_result.tool_result.success,
                    "data": step_result.tool_result.data,
                    "error": step_result.tool_result.error,
                }

                formatted_result = json.dumps(
                    tool_result_data,
                    indent=2,
                    default=str,
                )

                run.messages.append(
                    AgentMessage(
                        role="agent",
                        content=(
                            f"Tool result for step {step_result.step_id}:\n"
                            f"{formatted_result}"
                        ),
                    )
                )

            run.iterations += 1

            # Update the final agent state.
            if result.success:
                self._update_state(run, AgentState.COMPLETED)

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content="Agent execution completed successfully.",
                    )
                )

            else:
                self._update_state(run, AgentState.FAILED)
                run.error = result.error

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content=f"Agent execution failed: {result.error}",
                    )
                )

        except Exception as exc:
            self._update_state(run, AgentState.FAILED)
            run.error = str(exc)

            run.messages.append(
                AgentMessage(
                    role="system",
                    content=f"Agent run failed: {exc}",
                )
            )

        return run

    @staticmethod
    def _update_state(
        run: AgentRun,
        state: AgentState,
    ) -> None:
        run.state = state
        run.updated_at = datetime.now(timezone.utc)