from __future__ import annotations

from typing import Any

from .goal_training import GoalMazeSession
from .proprioception_temporal_analysis import analyze_proprioception_temporal_history
from .proprioception_temporal_observability import ProprioceptionTemporalRecorder


class TemporalGoalMazeSession(GoalMazeSession):
    """Goal-maze session with bounded human-only proprioception handoff history.

    The recorder observes only the proprioception payload returned by the existing
    neural-context handoff preparation. That means the sample has already passed
    the session's receptor validation and the Neural Context Firewall before it
    is copied into the diagnostic history.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.proprioception_temporal_recorder = ProprioceptionTemporalRecorder()

    def _prepare_brain_handoff(
        self,
        *,
        world_context: dict[str, Any],
        frame: Any,
        gustation: dict[str, Any],
        tactile: dict[str, Any],
        proprioception: dict[str, Any],
    ) -> tuple[Any, dict[str, Any]]:
        handoff_frame, handoff_context = super()._prepare_brain_handoff(
            world_context=world_context,
            frame=frame,
            gustation=gustation,
            tactile=tactile,
            proprioception=proprioception,
        )
        observed = handoff_context.get("proprioception")
        if not isinstance(observed, dict):
            raise ValueError("Neural handoff is missing validated proprioception")
        self.proprioception_temporal_recorder.observe_neural_handoff(observed)
        return handoff_frame, handoff_context

    def _snapshot_locked(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super()._snapshot_locked(*args, **kwargs)
        diagnostics = data.get("human_diagnostics")
        if not isinstance(diagnostics, dict):
            raise ValueError("GoalMazeSession human diagnostics contract is missing")
        history = self.proprioception_temporal_recorder.snapshot()
        diagnostics["proprioception_temporal"] = history
        diagnostics["proprioception_temporal_analysis"] = (
            analyze_proprioception_temporal_history(history)
        )
        return data
