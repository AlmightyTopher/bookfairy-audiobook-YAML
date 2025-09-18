"""
Risks Table Model
Risk documentation, mitigation tracking, and acceptance procedures
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class RiskSeverity(Enum):
    """Risk severity levels"""
    VERY_LOW = "very_low"          # Minor inconvenience
    LOW = "low"                  # Limited impact
    MEDIUM = "medium"            # Noticeable impact, manageable
    HIGH = "high"                # Significant impact
    CRITICAL = "critical"        # Severe impact, potential system failure
    BLOCKER = "blocker"          # Prevents deployment or major functionality


class RiskLikelihood(Enum):
    """How likely the risk is to occur"""
    VERY_UNLIKELY = "very_unlikely"  # <5% chance
    UNLIKELY = "unlikely"           # 5-15% chance
    POSSIBLE = "possible"           # 15-30% chance
    LIKELY = "likely"             # 30-50% chance
    VERY_LIKELY = "very_likely"   # 50-75% chance
    ALMOST_CERTAIN = "almost_certain"  # >75% chance


class RiskStatus(Enum):
    """Current status of the risk"""
    IDENTIFIED = "identified"         # Newly identified
    ASSESSED = "assessed"            # Assessment completed
    MITIGATION_PLANNED = "mitigation_planned"  # Mitigation plan developed
    MITIGATION_IN_PROGRESS = "mitigation_in_progress"  # Being mitigated
    MITIGATED = "mitigated"          # Successfully mitigated
    ACCEPTED = "accepted"           # Accepted without mitigation
    MONITORED = "monitored"         # Regularly monitored
    CLOSED = "closed"              # Risk no longer applicable
    ESCALATED = "escalated"        # Escalated to higher authority


@dataclass
class RiskEntry:
    """Individual risk entry in the risks table"""

    risk_id: str
    title: str
    description: str

    # Risk assessment
    severity: RiskSeverity = RiskSeverity.MEDIUM
    likelihood: RiskLikelihood = RiskLikelihood.POSSIBLE

    # Contextual information
    category: str = ""                           # e.g., "security", "performance", "reliability"
    component: str = ""                         # Which component/service/risk affects
    discovered_by: Optional[str] = None         # Who discovered this risk

    # Impact assessment
    impact_description: str = ""                # Detailed impact description
    business_impact: Optional[str] = None       # Business consequences
    technical_impact: Optional[str] = None      # Technical consequences
    user_impact: Optional[str] = None          # End-user consequences

    # Current status and tracking
    status: RiskStatus = RiskStatus.IDENTIFIED
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Mitigation planning and implementation
    mitigation_plan: Optional[str] = None       # How to mitigate the risk
    mitigation_owner: Optional[str] = None     # Who owns mitigation
    mitigation_due_date: Optional[datetime] = None
    mitigation_completed_date: Optional[datetime] = None

    # Risk acceptance (for accepted risks)
    acceptance_reason: Optional[str] = None    # Why risk was accepted
    acceptance_approver: Optional[str] = None  # Who approved acceptance
    acceptance_date: Optional[datetime] = None

    # Monitoring and controls
    monitoring_plan: Optional[str] = None      # How to monitor this risk
    early_warning_indicators: List[str] = field(default_factory=list)
    contingency_plan: Optional[str] = None     # What to do if risk materializes

    # Metadata and tracking
    related_findings: List[str] = field(default_factory=list)  # Related audit/findings
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # Documentation links, tickets, etc.

    def __post_init__(self):
        """Initialize risk entry"""
        if not self.risk_id:
            self.risk_id = f"risk_{int(datetime.utcnow().timestamp())}"

        # Auto-categorize if category not provided
        if not self.category:
            self._auto_categorize()

    def _auto_categorize(self):
        """Auto-categorize risk based on description keywords"""
        description_lower = (self.title + " " + self.description).lower()

        if any(keyword in description_lower for keyword in ["security", "breach", "vulnerable", "attack", "hack"]):
            self.category = "security"
        elif any(keyword in description_lower for keyword in ["performance", "slow", "latency", "response time", "speed"]):
            self.category = "performance"
        elif any(keyword in description_lower for keyword in ["reliability", "availability", "crash", "error", "failure"]):
            self.category = "reliability"
        elif any(keyword in description_lower for keyword in ["data", "database", "storage", "corruption", "loss"]):
            self.category = "data-integrity"
        elif any(keyword in description_lower for keyword in ["compliance", "legal", "audit", "regulatory"]):
            self.category = "compliance"
        elif any(keyword in description_lower for keyword in ["user experience", "ui", "usability", "interface"]):
            self.category = "user-experience"
        else:
            self.category = "uncategorized"

    def calculate_risk_score(self) -> float:
        """Calculate numerical risk score based on severity and likelihood"""

        severity_scores = {
            RiskSeverity.VERY_LOW: 1,
            RiskSeverity.LOW: 2,
            RiskSeverity.MEDIUM: 4,
            RiskSeverity.HIGH: 6,
            RiskSeverity.CRITICAL: 8,
            RiskSeverity.BLOCKER: 10
        }

        likelihood_scores = {
            RiskLikelihood.VERY_UNLIKELY: 0.1,
            RiskLikelihood.UNLIKELY: 0.3,
            RiskLikelihood.POSSIBLE: 0.6,
            RiskLikelihood.LIKELY: 0.8,
            RiskLikelihood.VERY_LIKELY: 0.9,
            RiskLikelihood.ALMOST_CERTAIN: 1.0
        }

        severity_score = severity_scores.get(self.severity, 4)
        likelihood_score = likelihood_scores.get(self.likelihood, 0.6)

        # Combined risk score (0.1 to 10.0)
        return severity_score * likelihood_score

    def get_risk_level(self) -> str:
        """Get descriptive risk level based on score"""
        score = self.calculate_risk_score()

        if score >= 8.0:
            return "Extreme Risk"
        elif score >= 6.0:
            return "High Risk"
        elif score >= 4.0:
            return "Medium Risk"
        elif score >= 2.0:
            return "Low Risk"
        else:
            return "Minimal Risk"

    def update_mitigation_plan(self, mitigation_plan: str, owner: str,
                             due_date: Optional[datetime] = None):
        """Update mitigation plan and ownership"""
        self.mitigation_plan = mitigation_plan
        self.mitigation_owner = owner
        self.mitigation_due_date = due_date
        self.status = RiskStatus.MITIGATION_PLANNED
        self.last_updated = datetime.utcnow()

    def mark_mitigation_complete(self):
        """Mark mitigation as completed"""
        self.status = RiskStatus.MITIGATED
        self.mitigation_completed_date = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def accept_risk(self, reason: str, approver: str):
        """Accept risk without mitigation"""
        self.acceptance_reason = reason
        self.acceptance_approver = approver
        self.acceptance_date = datetime.utcnow()
        self.status = RiskStatus.ACCEPTED
        self.last_updated = datetime.utcnow()

    def should_escalate(self) -> bool:
        """Check if risk should be escalated based on criteria"""

        # Critical/Blocker severity always escalate
        if self.severity in [RiskSeverity.CRITICAL, RiskSeverity.BLOCKER]:
            return True

        # High severity risks with high likelihood
        if (self.severity == RiskSeverity.HIGH and
            self.likelihood in [RiskLikelihood.LIKELY, RiskLikelihood.VERY_LIKELY, RiskLikelihood.ALMOST_CERTAIN]):
            return True

        # Risks past due date
        if self.mitigation_due_date and datetime.utcnow() > self.mitigation_due_date:
            return True

        # High-risk unmitigated items
        if (self.calculate_risk_score() >= 6.0 and
            self.status in [RiskStatus.IDENTIFIED, RiskStatus.ASSESSED]):
            return True

        return False

    def get_age_days(self) -> int:
        """Get age of risk entry in days"""
        delta = datetime.utcnow() - self.created_at
        return delta.days

    def is_due_for_review(self) -> bool:
        """Check if risk is due for periodic review"""
        days_since_update = (datetime.utcnow() - self.last_updated).days

        # Review frequency based on risk level
        risk_score = self.calculate_risk_score()

        if risk_score >= 8.0:  # Extreme risk
            return days_since_update >= 7  # Weekly review
        elif risk_score >= 6.0:  # High risk
            return days_since_update >= 14  # Bi-weekly review
        elif risk_score >= 4.0:  # Medium risk
            return days_since_update >= 30  # Monthly review
        else:  # Low/Minimal risk
            return days_since_update >= 90  # Quarterly review

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "likelihood": self.likelihood.value,
            "category": self.category,
            "component": self.component,
            "discovered_by": self.discovered_by,
            "impact_description": self.impact_description,
            "business_impact": self.business_impact,
            "technical_impact": self.technical_impact,
            "user_impact": self.user_impact,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "mitigation_plan": self.mitigation_plan,
            "mitigation_owner": self.mitigation_owner,
            "mitigation_due_date": self.mitigation_due_date.isoformat() if self.mitigation_due_date else None,
            "mitigation_completed_date": self.mitigation_completed_date.isoformat() if self.mitigation_completed_date else None,
            "acceptance_reason": self.acceptance_reason,
            "acceptance_approver": self.acceptance_approver,
            "acceptance_date": self.acceptance_date.isoformat() if self.acceptance_date else None,
            "monitoring_plan": self.monitoring_plan,
            "early_warning_indicators": self.early_warning_indicators,
            "contingency_plan": self.contingency_plan,
            "related_findings": self.related_findings,
            "tags": self.tags,
            "references": self.references,
            "calculated_risk_score": self.calculate_risk_score(),
            "risk_level": self.get_risk_level(),
            "should_escalate": self.should_escalate(),
            "age_days": self.get_age_days(),
            "due_for_review": self.is_due_for_review()
        }


@dataclass
class RisksTable:
    """Complete risks table with management and tracking capabilities"""

    table_id: str
    name: str
    description: str

    # Scope and context
    deliverable_name: str = ""                    # Associated deliverable or project
    environment: str = "development"              # Which environment this applies to

    # Risk entries
    risks: List[RiskEntry] = field(default_factory=list)

    # Table metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    owner: Optional[str] = None                   # Who owns/maintains this risks table

    # Review and approval
    review_frequency_days: int = 30               # How often to review
    last_review_date: Optional[datetime] = None
    approved_by: Optional[str] = None            # Stakeholder approval
    approval_date: Optional[datetime] = None

    # Status tracking
    overall_risk_level: str = "unknown"          # Aggregate risk level

    def __post_init__(self):
        """Initialize risks table"""
        if not self.table_id:
            self.table_id = f"rt_{int(datetime.utcnow().timestamp())}"

    def add_risk(self, risk: RiskEntry):
        """Add a risk entry to the table"""
        # Ensure risk_id is unique
        existing_ids = {r.risk_id for r in self.risks}
        if risk.risk_id in existing_ids:
            # Generate new ID if conflict
            risk.risk_id = f"risk_{int(datetime.utcnow().timestamp())}_{len(self.risks)}"

        self.risks.append(risk)
        self.last_updated = datetime.utcnow()
        self.update_overall_risk_level()

    def remove_risk(self, risk_id: str) -> bool:
        """Remove risk by ID, returns True if found and removed"""
        original_count = len(self.risks)
        self.risks = [r for r in self.risks if r.risk_id != risk_id]

        if len(self.risks) < original_count:
            self.last_updated = datetime.utcnow()
            self.update_overall_risk_level()
            return True
        return False

    def get_risk(self, risk_id: str) -> Optional[RiskEntry]:
        """Get risk by ID"""
        return next((r for r in self.risks if r.risk_id == risk_id), None)

    def get_risks_by_severity(self, severity: RiskSeverity) -> List[RiskEntry]:
        """Get all risks of a specific severity"""
        return [r for r in self.risks if r.severity == severity]

    def get_risks_by_category(self, category: str) -> List[RiskEntry]:
        """Get all risks in a specific category"""
        return [r for r in self.risks if r.category == category]

    def get_risks_by_status(self, status: RiskStatus) -> List[RiskEntry]:
        """Get all risks in a specific status"""
        return [r for r in self.risks if r.status == status]

    def get_high_priority_risks(self) -> List[RiskEntry]:
        """Get risks that require immediate attention"""
        high_risks = []

        # Blocker/Critical severity
        high_risks.extend(self.get_risks_by_severity(RiskSeverity.BLOCKER))
        high_risks.extend(self.get_risks_by_severity(RiskSeverity.CRITICAL))

        # Overdue mitigations
        current_time = datetime.utcnow()
        for risk in self.risks:
            if (risk.mitigation_due_date and
                current_time > risk.mitigation_due_date and
                risk.status not in [RiskStatus.MITIGATED, RiskStatus.CLOSED]):
                high_risks.append(risk)

        # Remove duplicates
        seen = set()
        unique_high_risks = []
        for risk in high_risks:
            if risk.risk_id not in seen:
                seen.add(risk.risk_id)
                unique_high_risks.append(risk)

        return unique_high_risks

    def get_risks_requiring_attention(self) -> List[RiskEntry]:
        """Get all risks that require attention"""
        attention_needed = []

        for risk in self.risks:
            if (risk.status == RiskStatus.IDENTIFIED or
                risk.should_escalate() or
                risk.is_due_for_review()):
                attention_needed.append(risk)

        return attention_needed

    def update_overall_risk_level(self):
        """Update overall risk level based on all risks"""
        if not self.risks:
            self.overall_risk_level = "no_risks"
            return

        # Calculate average risk score
        total_score = sum(r.calculate_risk_score() for r in self.risks)
        avg_score = total_score / len(self.risks)

        # Highest individual risk score
        max_score = max(r.calculate_risk_score() for r in self.risks)

        # Determine overall level based on worst individual risk and average
        if max_score >= 8.0 or avg_score >= 6.0:
            self.overall_risk_level = "extreme"
        elif max_score >= 6.0 or avg_score >= 4.0:
            self.overall_risk_level = "high"
        elif max_score >= 4.0 or avg_score >= 2.0:
            self.overall_risk_level = "medium"
        elif max_score >= 2.0 or avg_score >= 1.0:
            self.overall_risk_level = "low"
        else:
            self.overall_risk_level = "minimal"

    def can_proceed(self) -> tuple[bool, str]:
        """Check if deliverable can proceed based on risk assessment"""
        high_risks = self.get_risks_by_severity(RiskSeverity.BLOCKER)
        critical_risks = self.get_risks_by_severity(RiskSeverity.CRITICAL)

        unmitigated_high_risks = [
            r for r in high_risks + critical_risks
            if r.status not in [RiskStatus.MITIGATED, RiskStatus.ACCEPTED, RiskStatus.CLOSED]
        ]

        if unmitigated_high_risks:
            reason = f"Unmitigated high-impact risks: {len(unmitigated_high_risks)}"
            return False, reason

        # Check for overdue mitigations
        overdue_risks = [
            r for r in self.risks
            if r.mitigation_due_date and
               datetime.utcnow() > r.mitigation_due_date and
               r.status not in [RiskStatus.MITIGATED, RiskStatus.CLOSED]
        ]

        if overdue_risks:
            reason = f"Overdue risk mitigations: {len(overdue_risks)}"
            return False, reason

        return True, "All risks appropriately managed"

    def approve_for_acceptance(self, approver: str):
        """Approve risks table for production acceptance"""
        self.approved_by = approver
        self.approval_date = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def is_due_for_review(self) -> bool:
        """Check if table is due for periodic review"""
        if not self.last_review_date:
            return True

        days_since_review = (datetime.utcnow() - self.last_review_date).days
        return days_since_review >= self.review_frequency_days

    def conduct_review(self, reviewer: str):
        """Conduct periodic review"""
        self.last_review_date = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "name": self.name,
            "description": self.description,
            "deliverable_name": self.deliverable_name,
            "environment": self.environment,
            "risks": [r.to_dict() for r in self.risks],
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "owner": self.owner,
            "review_frequency_days": self.review_frequency_days,
            "last_review_date": self.last_review_date.isoformat() if self.last_review_date else None,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "overall_risk_level": self.overall_risk_level,
            "total_risks": len(self.risks),
            "high_priority_risks": len(self.get_high_priority_risks()),
            "attention_needed": len(self.get_risks_requiring_attention()),
            "due_for_review": self.is_due_for_review()
        }
