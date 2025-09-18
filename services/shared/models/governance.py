"""
Audit Lens Framework Model
Universal Audit Lens governance system for BookFairy
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum


class AuditLens(Enum):
    """The 13 Universal Audit Lenses"""
    ASSUMPTIONS = "assumptions"                      # Challenge default assumptions
    BEST_PRACTICES = "best-practices"               # Apply industry best practices
    EDGE_CASES = "edge-cases"                       # Consider unusual scenarios
    SAFETY_SECURITY = "safety-security"            # Evaluate security and safety
    SCALABILITY_GROWTH = "scalability"             # Plan for growth
    PERFORMANCE_EFFICIENCY = "performance"         # Optimize performance
    RELIABILITY_CONTINUITY = "reliability"          # Ensure system reliability
    OBSERVABILITY_FEEDBACK = "observability"        # Monitor and observe
    COMMUNICATION_CLARITY = "communication"        # Clear communication
    COST_SUSTAINABILITY = "cost"                   # Economic considerations
    HUMAN_FACTORS = "human-factors"                # Human usability factors
    SELF_CONSISTENCY = "self-consistency"           # Internal consistency
    REGRET_LATER = "regret-later"                   # Long-term maintainability


class AuditSeverity(Enum):
    """Severity levels for audit findings"""
    BLOCKER = "blocker"         # Must fix before proceeding
    HIGH = "high"              # Should fix as soon as possible
    MEDIUM = "medium"          # Consider fixing in current cycle
    LOW = "low"               # Nice to fix when possible
    INFO = "info"             # For awareness only


@dataclass
class AuditFinding:
    """Represents a finding from an audit lens evaluation"""

    finding_id: str
    lens_name: AuditLens
    target_component: str  # Component being evaluated

    # Finding details
    title: str
    description: str
    severity: AuditSeverity = AuditSeverity.MEDIUM

    # Evidence and recommendations
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    # Status and tracking
    status: str = "open"  # open, addressed, rejected, accepted_as_risk
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Resolution
    resolution_plan: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    # Risk acceptance (for MEDIUM/LOW findings)
    accepted_risk: bool = False
    risk_mitigation: Optional[str] = None

    def __post_init__(self):
        """Initialize audit finding"""
        if not self.finding_id:
            self.finding_id = f"aud-{self.lens_name.value[:3]}-{int(datetime.utcnow().timestamp())}"

    def resolve(self, resolution_plan: str, resolved_by: str):
        """Mark finding as resolved"""
        self.status = "addressed"
        self.resolution_plan = resolution_plan
        self.resolved_by = resolved_by
        self.resolved_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def accept_as_risk(self, mitigation: Optional[str] = None):
        """Accept finding as acceptable risk"""
        self.accepted_risk = True
        self.status = "accepted_as_risk"
        self.risk_mitigation = mitigation
        self.last_updated = datetime.utcnow()

    def reject(self):
        """Reject finding as not applicable"""
        self.status = "rejected"
        self.last_updated = datetime.utcnow()

    def is_blocking(self) -> bool:
        """Check if finding is blocking (Blocker severity or High and unaddressed)"""
        return (
            self.severity == AuditSeverity.BLOCKER or
            (self.severity == AuditSeverity.HIGH and self.status == "open")
        )

    def get_age_days(self) -> int:
        """Get age of finding in days"""
        delta = datetime.utcnow() - self.created_at
        return delta.days

    def should_escalate(self) -> bool:
        """Check if finding should be escalated based on age and severity"""
        age_days = self.get_age_days()

        if self.severity == AuditSeverity.BLOCKER and age_days > 1:
            return True
        elif self.severity == AuditSeverity.HIGH and age_days > 3:
            return True
        elif self.severity == AuditSeverity.MEDIUM and age_days > 7:
            return True
        elif self.severity == AuditSeverity.LOW and age_days > 14:
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "lens_name": self.lens_name.value,
            "target_component": self.target_component,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "resolution_plan": self.resolution_plan,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "accepted_risk": self.accepted_risk,
            "risk_mitigation": self.risk_mitigation,
            "age_days": self.get_age_days(),
            "should_escalate": self.should_escalate(),
            "is_blocking": self.is_blocking()
        }


@dataclass
class AuditLensDefinition:
    """Definition of an audit lens with evaluation criteria"""

    lens: AuditLens

    # Basic information
    name: str
    description: str
    category: str  # safety, performance, governance, etc.

    # Evaluation criteria
    questions: List[str] = field(default_factory=list)
    criteria: Dict[str, Any] = field(default_factory=dict)

    # Scoring
    max_score: float = 1.0
    scoring_method: str = "manual"  # manual, automated, hybrid

    # Automation
    evaluator_function: Optional[Callable] = None  # Function to auto-evaluate lens

    def __post_init__(self):
        """Initialize audit lens definition based on lens type"""
        self._set_default_definition()

    def _set_default_definition(self):
        """Set default definition based on audit lens type"""
        lens_defaults = {
            AuditLens.ASSUMPTIONS: {
                "name": "Assumptions Challenge",
                "description": "Challenge default assumptions that may lead to system failures",
                "category": "governance",
                "questions": [
                    "What assumptions are we making about system behavior?",
                    "How would the system behave if these assumptions were wrong?",
                    "What would be the impact of incorrect assumptions?"
                ]
            },
            AuditLens.BEST_PRACTICES: {
                "name": "Best Practices Application",
                "description": "Apply industry best practices and standards",
                "category": "quality",
                "questions": [
                    "What industry standards apply to this component?",
                    "Are we following established best practices?",
                    "What lessons can be learned from similar systems?"
                ]
            },
            AuditLens.EDGE_CASES: {
                "name": "Edge Cases Analysis",
                "description": "Consider unusual but possible scenarios",
                "category": "reliability",
                "questions": [
                    "What unusual inputs or conditions could occur?",
                    "How does the system handle extreme edge cases?",
                    "Are there boundary conditions that haven't been tested?"
                ]
            },
            AuditLens.SAFETY_SECURITY: {
                "name": "Safety & Security Review",
                "description": "Evaluate safety and security implications",
                "category": "safety",
                "questions": [
                    "What security vulnerabilities exist?",
                    "How could the system be compromised?",
                    "What safety concerns apply to users?"
                ]
            }
        }

        if self.lens in lens_defaults:
            defaults = lens_defaults[self.lens]
            self.name = defaults["name"]
            self.description = defaults["description"]
            self.category = defaults["category"]
            self.questions = defaults["questions"]

    def evaluate(self, target: Any) -> Dict[str, Any]:
        """Evaluate a target using this audit lens"""
        if self.evaluator_function:
            return self.evaluator_function(target, self)
        else:
            # Manual evaluation placeholder
            return {
                "lens_name": self.lens.value,
                "score": 0.5,  # Default neutral score
                "findings": [],
                "evaluation_method": "manual",
                "requires_human_review": True
            }


class AuditLensFramework:
    """Framework for managing and applying audit lenses"""

    def __init__(self):
        self.lens_definitions: Dict[AuditLens, AuditLensDefinition] = {}
        self.findings: List[AuditFinding] = []
        self.audit_history: List[Dict[str, Any]] = []

        # Initialize all audit lens definitions
        self._initialize_lens_definitions()

    def _initialize_lens_definitions(self):
        """Initialize all audit lens definitions"""
        all_lenses = [
            AuditLens.ASSUMPTIONS,
            AuditLens.BEST_PRACTICES,
            AuditLens.EDGE_CASES,
            AuditLens.SAFETY_SECURITY,
            AuditLens.SCALABILITY_GROWTH,
            AuditLens.PERFORMANCE_EFFICIENCY,
            AuditLens.RELIABILITY_CONTINUITY,
            AuditLens.OBSERVABILITY_FEEDBACK,
            AuditLens.COMMUNICATION_CLARITY,
            AuditLens.COST_SUSTAINABILITY,
            AuditLens.HUMAN_FACTORS,
            AuditLens.SELF_CONSISTENCY,
            AuditLens.REGRET_LATER
        ]

        for lens in all_lenses:
            self.lens_definitions[lens] = AuditLensDefinition(lens=lens)

    def apply_lens(self, lens: AuditLens, target_component: Any,
                  evaluator_config: Optional[Dict[str, Any]] = None) -> List[AuditFinding]:
        """Apply a specific audit lens to a target component"""
        lens_definition = self.lens_definitions.get(lens)
        if not lens_definition:
            return []

        # Record audit attempt
        audit_record = {
            "lens_name": lens.value,
            "target_component": getattr(target_component, 'name', str(type(target_component))),
            "timestamp": datetime.utcnow().isoformat(),
            "config": evaluator_config
        }
        self.audit_history.append(audit_record)

        # Apply the lens
        evaluation_result = lens_definition.evaluate(target_component)

        # Convert evaluation results to findings
        findings = []
        for finding_data in evaluation_result.get("findings", []):
            finding = AuditFinding(
                lens_name=lens,
                target_component=getattr(target_component, 'name', str(type(target_component))),
                title=finding_data.get("title", "Audit Finding"),
                description=finding_data.get("description", ""),
                severity=AuditSeverity(finding_data.get("severity", "medium")),
                evidence=finding_data.get("evidence", {}),
                recommendations=finding_data.get("recommendations", [])
            )
            findings.append(finding)
            self.findings.append(finding)

        return findings

    def apply_all_lenses(self, target_component: Any) -> Dict[str, List[AuditFinding]]:
        """Apply all audit lenses to a target component"""
        all_findings = {}

        for lens in AuditLens:
            findings = self.apply_lens(lens, target_component)
            all_findings[lens.value] = findings

        return all_findings

    def get_blocking_findings(self) -> List[AuditFinding]:
        """Get all blocking (Blocker severity) findings"""
        return [finding for finding in self.findings if finding.is_blocking()]

    def get_findings_by_severity(self, severity: AuditSeverity) -> List[AuditFinding]:
        """Get findings by severity level"""
        return [finding for finding in self.findings if finding.severity == severity]

    def get_findings_requiring_attention(self) -> List[AuditFinding]:
        """Get findings that require attention (open and unaddressed)"""
        return [finding for finding in self.findings if finding.status == "open"]

    def get_overview_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit lens overview report"""
        total_findings = len(self.findings)
        open_findings = len(self.get_findings_requiring_attention())
        blocking_findings = len(self.get_blocking_findings())

        # Findings by severity
        severity_counts = {}
        for severity in AuditSeverity:
            severity_counts[severity.value] = len(self.get_findings_by_severity(severity))

        # Findings by lens
        lens_counts = {}
        for lens in AuditLens:
            lens_counts[lens.value] = sum(
                1 for finding in self.findings
                if finding.lens_name == lens
            )

        # Findings needing attention by age
        old_findings = sum(1 for finding in self.findings
                          if finding.should_escalate() and finding.status == "open")

        return {
            "total_findings": total_findings,
            "open_findings": open_findings,
            "blocking_findings": blocking_findings,
            "by_severity": severity_counts,
            "by_lens": lens_counts,
            "old_findings_needing_escalation": old_findings,
            "audit_lens_compliance_score": self._calculate_compliance_score(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _calculate_compliance_score(self) -> float:
        """Calculate overall compliance score based on findings"""
        if not self.findings:
            return 1.0  # No findings means perfect compliance

        # Weight findings by severity
        severity_weights = {
            AuditSeverity.BLOCKER: 10,
            AuditSeverity.HIGH: 5,
            AuditSeverity.MEDIUM: 2,
            AuditSeverity.LOW: 1,
            AuditSeverity.INFO: 0.5
        }

        total_weight = 0.0
        resolved_weight = 0.0

        for finding in self.findings:
            weight = severity_weights[finding.severity]

            if finding.status in ["addressed", "accepted_as_risk"]:
                resolved_weight += weight * (1 if finding.accepted_risk else 1)

            total_weight += weight

        if total_weight == 0:
            return 1.0

        return resolved_weight / total_weight

    def export_findings(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Export all findings in a structured format"""
        export_data = []

        for finding in self.findings:
            if not include_resolved and finding.status in ["addressed", "accepted_as_risk", "rejected"]:
                continue

            export_data.append({
                "audit_lens": finding.lens_name.value,
                "component": finding.target_component,
                "title": finding.title,
                "severity": finding.severity.value,
                "status": finding.status,
                "age_days": finding.get_age_days(),
                "should_escalate": finding.should_escalate(),
                "data": finding.to_dict()
            })

        return export_data
