from dataclasses import dataclass
from typing import Any

ACTION_POLICY_PATHS = {
    "summarize_ticket": "support.read_only",
    "draft_customer_reply": "support.read_only",
    "refund_customer": "support.refund",
}

ROLE_ACTIONS = {
    "support_viewer": {"summarize_ticket", "draft_customer_reply"},
    "support_agent": {"summarize_ticket", "draft_customer_reply"},
    "billing_manager": {"summarize_ticket", "draft_customer_reply", "refund_customer"},
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def authorize_action(
    principal: Principal, action: str, context: dict[str, Any]
) -> AuthorizationDecision:
    expected_policy_path = ACTION_POLICY_PATHS.get(action)
    if expected_policy_path is None:
        return AuthorizationDecision(False, f"Unknown action: {action}")

    context_tenant = context.get("tenant_id")
    if context_tenant != principal.tenant_id:
        return AuthorizationDecision(False, "Tenant context does not match principal")

    context_user = context.get("user")
    if context_user and context_user != principal.user_id:
        return AuthorizationDecision(False, "User context does not match principal")

    if context.get("policy_path") != expected_policy_path:
        return AuthorizationDecision(
            False, f"Context is not bound to policy path: {expected_policy_path}"
        )

    allowed_actions = set()
    for role in principal.roles:
        allowed_actions.update(ROLE_ACTIONS.get(role, set()))

    if action not in allowed_actions:
        return AuthorizationDecision(False, f"Principal is not allowed to perform action: {action}")

    return AuthorizationDecision(True, "allowed")
