import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SecretRule:
    name: str
    pattern: re.Pattern
    min_entropy: float = 3.0
    description: str = ""


SECRET_RULES: List[SecretRule] = [
    SecretRule(
        name="AWS Access Key ID",
        pattern=re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        min_entropy=2.8,
        description="Matched standard AWS Access Key ID format",
    ),
    SecretRule(
        name="AWS Secret Access Key",
        pattern=re.compile(r"(?i)\baws_secret_access_key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?\b"),
        min_entropy=4.2,
        description="Matched AWS Secret Access Key assignment",
    ),
    SecretRule(
        name="GitHub Personal Access Token",
        pattern=re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b"),
        min_entropy=3.5,
        description="Matched GitHub Personal Access Token pattern",
    ),
    SecretRule(
        name="Slack Webhook URL",
        pattern=re.compile(r"(https://hooks\.slack[^/]+/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+)"),
        min_entropy=3.0,
        description="Matched Slack Incoming Webhook URL",
    ),
    SecretRule(
        name="JSON Web Token (JWT)",
        pattern=re.compile(r"\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b"),
        min_entropy=4.0,
        description="Matched JWT bearer token pattern",
    ),
    SecretRule(
        name="Private Key Header",
        pattern=re.compile(r"(-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)?\s*PRIVATE KEY-----)"),
        min_entropy=0.0,  # Header itself has low entropy, but key structure is definite
        description="Matched Private Key PEM header",
    ),
    SecretRule(
        name="Generic Secret Assignment",
        pattern=re.compile(
            r"(?i)\b(?:api_key|secret|password|token|auth_key|access_token)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
        ),
        min_entropy=3.5,
        description="Matched generic credential string assignment",
    ),
]
