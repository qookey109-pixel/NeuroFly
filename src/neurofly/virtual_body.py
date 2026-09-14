from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .proprioception import feco_motion_proprioception, proprioceptive_channel_levels


VIRTUAL_BODY_MODEL = "neurofly-representative-feco-joint-body-v0.1"
VIRTUAL_BODY_POLICY = "stateful-motor-execution-to-private-joint-mechanics-no-world-kinematics"
VIRTUAL_BODY_STATE_SCHEMA = "neurofly-representative-feco-joint-body-state-v0.1"
MOTOR_EXECUTIONS = frozenset({"HOLD", "FORWARD", "TURN_LEFT", "TURN_RIGHT"})


def _bounded_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = 0.0
    return max(0.0, min(1.0, number))


@dataclass(slots=True)
class VirtualFeCOJointBody:
    """Stateful representative femur-tibia joint used before six-leg mapping exists.

    The private state is an engineering body proxy. It converts *executed motor
    mode* into internal joint mechanics, then sends only receptor-domain motion
    channels through :func:`feco_motion_proprioception`.

    World coordinates, heading, world displacement, route state and reward are
    intentionally absent from this API. Left/right turns share the same
    representative-joint mechanics so the proxy cannot reveal turn direction as
    a hidden one-hot motor command. This class is not a six-leg locomotion model.
    """

    joint_phase: float = 0.0
    joint_position: float = 0.0
    step_index: int = 0
    last_motor_execution: str = "HOLD"

    def reset(self) -> None:
        self.joint_phase = 0.0
        self.joint_position = 0.0
        self.step_index = 0
        self.last_motor_execution = "HOLD"

    @staticmethod
    def _target_for_execution(
        *,
        joint_phase: float,
        joint_position: float,
        motor_execution: str,
    ) -> tuple[float, float]:
        if motor_execution == "HOLD":
            # Passive return toward a neutral representative joint. A HOLD after
            # movement may therefore still create real proprioceptive motion.
            return joint_phase, joint_position * 0.5

        # These phase increments and amplitudes are explicit engineering values,
        # not measured Drosophila joint mechanics. FORWARD uses a full excursion;
        # turns use a smaller representative excursion. TURN_LEFT and TURN_RIGHT
        # are deliberately identical because this proxy has no leg laterality.
        if motor_execution == "FORWARD":
            phase_step = 0.25
            amplitude = 1.0
        else:
            phase_step = 0.125
            amplitude = 0.65

        next_phase = (joint_phase + phase_step) % 1.0
        target = amplitude * math.sin(2.0 * math.pi * next_phase)
        return next_phase, target

    def advance(
        self,
        motor_execution: str,
        *,
        mechanical_vibration: float = 0.0,
    ) -> dict[str, Any]:
        """Advance private joint mechanics and return only FeCO-like channels.

        ``motor_execution`` must describe the action that the body actually
        executed, after any controller override. It is never copied into the
        returned neural payload. ``mechanical_vibration`` is likewise an internal
        body/environment magnitude; v0.1 does not synthesize vibration on its own.
        """

        execution = str(motor_execution).strip().upper()
        if execution not in MOTOR_EXECUTIONS:
            raise ValueError(f"Unknown virtual body motor execution: {motor_execution}")

        previous_position = float(self.joint_position)
        next_phase, next_position = self._target_for_execution(
            joint_phase=float(self.joint_phase),
            joint_position=previous_position,
            motor_execution=execution,
        )
        joint_delta = next_position - previous_position

        self.joint_phase = float(next_phase)
        self.joint_position = max(-1.0, min(1.0, float(next_position)))
        self.step_index += 1
        self.last_motor_execution = execution

        payload = feco_motion_proprioception(
            joint_delta=joint_delta,
            vibration=_bounded_unit(mechanical_vibration),
        )
        # Fail at the body boundary if a future edit violates the receptor
        # contract before any session or neural runtime can consume it.
        proprioceptive_channel_levels(payload)
        return payload

    def persistence_snapshot(self) -> dict[str, Any]:
        """Return private body state for checkpoints/human diagnostics only."""

        return {
            "schema": VIRTUAL_BODY_STATE_SCHEMA,
            "model": VIRTUAL_BODY_MODEL,
            "policy": VIRTUAL_BODY_POLICY,
            "representative_joint_only": True,
            "six_leg_model": False,
            "joint_phase": float(self.joint_phase),
            "joint_position": float(self.joint_position),
            "step_index": int(self.step_index),
            "motor_execution": str(self.last_motor_execution),
        }

    def restore(self, payload: dict[str, Any]) -> None:
        if payload.get("schema") != VIRTUAL_BODY_STATE_SCHEMA:
            raise ValueError("Unsupported virtual body state schema")
        if payload.get("model") != VIRTUAL_BODY_MODEL:
            raise ValueError("Unsupported virtual body model")
        if payload.get("policy") != VIRTUAL_BODY_POLICY:
            raise ValueError("Unsupported virtual body policy")
        if payload.get("representative_joint_only") is not True:
            raise ValueError("Virtual body v0.1 must remain representative-joint only")
        if payload.get("six_leg_model") is not False:
            raise ValueError("Virtual body v0.1 must not claim a six-leg model")

        phase = float(payload.get("joint_phase", 0.0))
        position = float(payload.get("joint_position", 0.0))
        step_index = int(payload.get("step_index", 0))
        execution = str(payload.get("motor_execution", "HOLD")).strip().upper()
        if not 0.0 <= phase < 1.0:
            raise ValueError("Virtual joint phase must stay within [0,1)")
        if not -1.0 <= position <= 1.0:
            raise ValueError("Virtual joint position must stay within [-1,1]")
        if step_index < 0:
            raise ValueError("Virtual body step index must be non-negative")
        if execution not in MOTOR_EXECUTIONS:
            raise ValueError("Invalid persisted virtual body motor execution")

        self.joint_phase = phase
        self.joint_position = position
        self.step_index = step_index
        self.last_motor_execution = execution
