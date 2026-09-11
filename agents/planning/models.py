from enum import Enum


class ExecutionPhase(str, Enum):
    """Phases in the agent's goal resolution lifecycle."""

    INVESTIGATION = "investigation"
    POLICY_CHECK = "policy_check"
    PRE_ACTION_VERIFICATION = "pre_action_verification"
    ACTION_EXECUTION = "action_execution"
    POST_ACTION_VERIFICATION = "post_action_verification"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    AWAITING_APPROVAL = "awaiting_approval"
