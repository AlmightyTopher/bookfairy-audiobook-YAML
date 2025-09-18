"""
Governance Compliance Report Model
Comprehensive audit reporting and compliance tracking for BookFairy
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class ComplianceStatus(Enum):
    """Overall compliance status for reports"""
    COMPLIANT = "compliant"                      # All requirements met
    NON_COMPLIANT = "non_compliant"             # Critical requirements not met
    PARTIAL_COMPLIANCE = "partial_compliance"   # Some requirements met
    NO_DATA = "no_data"                         # Insufficient data to assess
    EXEMPTED = "exempted"                      # Temporarily exempted


class ReportSection(Enum):
    """Sections included in compliance reports"""
    EXECUTIVE_SUMMARY = "executive_summary"
    AUDIT_LENS_RESULTS = "audit_lens_results"
    RISK_ASSESSMENT = "risk_assessment"
    TERMINATION_CRITERIA = "termination_criteria"
    VALIDATION_PROTOCOL = "validation_protocol"
    PERFORMANCE_METRICS = "performance_metrics"
    SECURITY_SCANNING = "security_scanning"
    RECOMMENDATIONS = "recommendations"


@dataclass
class ComplianceFinding:
    """Individual compliance finding or issue"""

    finding_id: str
    title: str
    description: str

    # Classification
    severity_level: str = "info"  # blocker, critical, major, minor, info
    category: str = ""  # security, performance, governance, etc.

    # Impact and evidence
    impact_description: str = ""
    evidence_collected: List[Dict[str, Any]] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)

    # Status and tracking
    status: str = "open"  # open, in_progress, resolved, dismissed
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None

    # Audit trail
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize compliance finding"""
        if not self.finding_id:
            self.finding_id = f"find_{int(datetime.utcnow().timestamp())}"

    def record_evidence(self, evidence_data: Dict[str, Any], collector: str):
        """Record evidence for this finding"""
        evidence_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": evidence_data,
            "collected_by": collector
        }
        self.evidence_collected.append(evidence_entry)

    def update_status(self, new_status: str, updater: str, notes: Optional[str] = None):
        """Update finding status with audit trail"""
        status_change = {
            "timestamp": datetime.utcnow().isoformat(),
            "previous_status": self.status,
            "new_status": new_status,
            "changed_by": updater,
            "notes": notes
        }
        self.audit_trail.append(status_change)
        self.status = new_status

        if new_status in ["resolved", "dismissed"]:
            self.resolved_at = datetime.utcnow()

    def resolve(self, resolver: str, resolution_notes: Optional[str] = None):
        """Mark finding as resolved"""
        self.update_status("resolved", resolver, resolution_notes)

    def dismiss(self, dismisser: str, dismissal_reason: str):
        """Dismiss findings as not applicable"""
        self.update_status("dismissed", dismisser, dismissal_reason)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "description": self.description,
            "severity_level": self.severity_level,
            "category": self.category,
            "impact_description": self.impact_description,
            "evidence_collected": self.evidence_collected,
            "remediation_steps": self.remediation_steps,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "assigned_to": self.assigned_to,
            "audit_trail": self.audit_trail,
            "age_days": self.get_age_days()
        }

    def get_age_days(self) -> int:
        """Get age in days"""
        resolution_time = self.resolved_at if self.resolved_at else datetime.utcnow()
        return (resolution_time - self.created_at).days


@dataclass
class ComplianceSection:
    """Individual section of a compliance report"""

    section_name: ReportSection
    title: str
    description: str

    # Content
    overall_status: ComplianceStatus = ComplianceStatus.NO_DATA
    score_percentage: float = 0.0
    findings: List[ComplianceFinding] = field(default_factory=list)

    # Metrics and data
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary_data: Dict[str, Any] = field(default_factory=dict)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    priority_actions: List[str] = field(default_factory=list)

    def calculate_section_score(self) -> float:
        """Calculate compliance score for this section"""

        # Base score on status
        status_scores = {
            ComplianceStatus.COMPLIANT: 100.0,
            ComplianceStatus.PARTIAL_COMPLIANCE: 60.0,
            ComplianceStatus.NON_COMPLIANT: 20.0,
            ComplianceStatus.NO_DATA: 0.0,
            ComplianceStatus.EXEMPTED: 80.0
        }

        base_score = status_scores.get(self.overall_status, 0.0)

        # Adjust based on findings severity
        if self.findings:
            blocker_count = sum(1 for f in self.findings if f.severity_level == "blocker")
            critical_count = sum(1 for f in self.findings if f.severity_level == "critical")
            major_count = sum(1 for f in self.findings if f.severity_level == "major")

            # Penalties for critical findings
            penalty = (blocker_count * 30 + critical_count * 20 + major_count * 10)
            base_score = max(0.0, base_score - penalty)

        self.score_percentage = base_score
        return base_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_name": self.section_name.value,
            "title": self.title,
            "description": self.description,
            "overall_status": self.overall_status.value,
            "score_percentage": self.score_percentage,
            "findings_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "metrics": self.metrics,
            "summary_data": self.summary_data,
            "recommendations": self.recommendations,
            "priority_actions": self.priority_actions
        }


@dataclass
class GovernanceComplianceReport:
    """Comprehensive governance compliance report for BookFairy"""

    report_id: str
    report_title: str
    deliverable_name: str

    # Report scope and context
    environment: str = "development"  # development, staging, production
    scope_description: str = ""
    assessor: Optional[str] = None

    # Time period
    report_period_start: datetime = field(default_factory=lambda: datetime.utcnow() - timedelta(days=30))
    report_period_end: datetime = field(default_factory=datetime.utcnow)

    # Report sections
    sections: Dict[ReportSection, ComplianceSection] = field(default_factory=dict)

    # Overall report status
    overall_status: ComplianceStatus = ComplianceStatus.NO_DATA
    overall_score: float = 0.0

    # Executive summary
    executive_summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    critical_actions: List[str] = field(default_factory=list)

    # Approval and review
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def __post_init__(self):
        """Initialize compliance report"""
        if not self.report_id:
            self.report_id = f"cr_{int(datetime.utcnow().timestamp())}"

        # Initialize default sections if not provided
        self._initialize_default_sections()

    def _initialize_default_sections(self):
        """Initialize default compliance sections"""
        default_sections = {
            ReportSection.EXECUTIVE_SUMMARY: (
                "Executive Summary",
                "High-level overview of compliance status and key findings"
            ),
            ReportSection.AUDIT_LENS_RESULTS: (
                "Universal Audit Lens Results",
                "Application of all 13 universal audit lenses"
            ),
            ReportSection.RISK_ASSESSMENT: (
                "Risk Assessment",
                "Comprehensive risk assessment and mitigation tracking"
            ),
            ReportSection.TERMINATION_CRITERIA: (
                "Termination Criteria",
                "Assessment against project termination conditions"
            ),
            ReportSection.VALIDATION_PROTOCOL: (
                "Validation Protocol",
                "Status of validation steps and green-light confirmation"
            ),
            ReportSection.PERFORMANCE_METRICS: (
                "Performance Metrics",
                "System performance against defined requirements"
            ),
            ReportSection.SECURITY_SCANNING: (
                "Security Scanning",
                "Security assessment and vulnerability findings"
            ),
            ReportSection.RECOMMENDATIONS: (
                "Recommendations",
                "Action items and improvement suggestions"
            )
        }

        for section_enum, (title, description) in default_sections.items():
            if section_enum not in self.sections:
                self.sections[section_enum] = ComplianceSection(
                    section_name=section_enum,
                    title=title,
                    description=description
                )

    def add_finding(self, section: ReportSection, finding: ComplianceFinding):
        """Add compliance finding to specific section"""
        if section not in self.sections:
            self.sections[section] = ComplianceSection(
                section_name=section,
                title=section.value.replace("_", " ").title(),
                description=f"Findings related to {section.value}"
            )

        self.sections[section].findings.append(finding)
        self.last_updated = datetime.utcnow()

    def calculate_overall_score(self) -> float:
        """Calculate overall compliance score across all sections"""

        section_scores = []
        section_weights = {
            ReportSection.EXECUTIVE_SUMMARY: 0.05,
            ReportSection.AUDIT_LENS_RESULTS: 0.30,
            ReportSection.RISK_ASSESSMENT: 0.25,
            ReportSection.TERMINATION_CRITERIA: 0.15,
            ReportSection.VALIDATION_PROTOCOL: 0.10,
            ReportSection.PERFORMANCE_METRICS: 0.10,
            ReportSection.SECURITY_SCANNING: 0.10,
            ReportSection.RECOMMENDATIONS: 0.05
        }

        total_weight = 0.0
        weighted_score = 0.0

        for section_enum, section in self.sections.items():
            score = section.calculate_section_score()
            weight = section_weights.get(section_enum, 0.1)

            weighted_score += score * weight
            total_weight += weight

        if total_weight > 0:
            self.overall_score = weighted_score / total_weight
        else:
            self.overall_score = 0.0

        # Update overall status based on score
        if self.overall_score >= 90.0:
            self.overall_status = ComplianceStatus.COMPLIANT
        elif self.overall_score >= 60.0:
            self.overall_status = ComplianceStatus.PARTIAL_COMPLIANCE
        elif self.overall_score >= 10.0:
            self.overall_status = ComplianceStatus.NON_COMPLIANT
        else:
            self.overall_status = ComplianceStatus.NO_DATA

        return self.overall_score

    def get_finding_summary_by_category(self) -> Dict[str, Dict[str, int]]:
        """Summarize findings by category and severity"""

        summary = {}

        for section in self.sections.values():
            for finding in section.findings:
                category = finding.category or "uncategorized"
                severity = finding.severity_level

                if category not in summary:
                    summary[category] = {}

                if severity not in summary[category]:
                    summary[category][severity] = 0

                summary[category][severity] += 1

        return summary

    def get_overdue_findings(self, days_threshold: int = 14) -> List[ComplianceFinding]:
        """Get findings that have been open for too long"""
        overdue = []
        cutoff_date = self.created_at + timedelta(days=days_threshold)

        for section in self.sections.values():
            for finding in section.findings:
                if finding.status == "open" and finding.created_at < cutoff_date:
                    overdue.append(finding)

        return overdue

    def get_critical_findings(self) -> List[ComplianceFinding]:
        """Get critical/blocker level findings"""
        critical = []

        for section in self.sections.values():
            for finding in section.findings:
                if finding.severity_level in ["blocker", "critical"]:
                    critical.append(finding)

        return critical

    def generate_executive_summary(self) -> str:
        """Generate executive summary based on report data"""

        total_findings = sum(len(s.findings) for s in self.sections.values())
        critical_findings = len(self.get_critical_findings())
        overdue_findings = len(self.get_overdue_findings())

        summary_parts = [
            f"Compliance report for '{self.deliverable_name}' - {self.environment} environment",
            f"Overall compliance status: {self.overall_status.value}",
            f"Overall score: {self.overall_score:.1f}%",
            f"Generated: {self.created_at.strftime('%Y-%m-%d')}"
        ]

        statistics_parts = []
        if total_findings > 0:
            statistics_parts.append(f"Total findings: {total_findings}")
        if critical_findings > 0:
            statistics_parts.append(f"Critical findings: {critical_findings}")
        if overdue_findings > 0:
            statistics_parts.append(f"Overdue findings: {overdue_findings}")

        if statistics_parts:
            summary_parts.append(" | ".join(statistics_parts))

        # Add key insights
        if self.overall_score >= 90.0:
            summary_parts.append("✅ All governance requirements met - ready for production")
        elif self.overall_score >= 60.0:
            summary_parts.append("⚠️ Partial compliance - specific concerns require attention")
        else:
            summary_parts.append("❌ Critical compliance issues requiring immediate action")

        self.executive_summary = ". ".join(summary_parts) + "."
        return self.executive_summary

    def approve_report(self, approver: str):
        """Approve the compliance report"""
        self.approved_by = approver
        self.approval_date = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def can_be_approved(self) -> tuple[bool, str]:
        """Check if report meets approval criteria"""
        critical_count = len(self.get_critical_findings())
        overdue_count = len(self.get_overdue_findings())

        if critical_count > 0:
            return False, f"Report has {critical_count} critical findings requiring resolution"

        if overdue_count > 0:
            return False, f"Report has {overdue_count} overdue findings requiring attention"

        if self.overall_score < 60.0:
            return False, f"Overall score {self.overall_score:.1f}% is below approval threshold"

        return True, "Report meets all approval criteria"

    def export_stakeholder_report(self, stakeholder_type: str) -> Dict[str, Any]:
        """Export report tailored for specific stakeholder type"""

        # Base report structure
        stakeholder_report = {
            "report_id": self.report_id,
            "deliverable_name": self.deliverable_name,
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "executive_summary": self.executive_summary,
            "generated_at": datetime.utcnow().isoformat(),
            "stakeholder_focus": stakeholder_type
        }

        # Customize content based on stakeholder type
        if stakeholder_type == "engineering":
            # Technical details, findings by component
            findings_by_category = self.get_finding_summary_by_category()
            stakeholder_report["technical_details"] = findings_by_category
            stakeholder_report["key_metrics"] = self._get_technical_metrics()

        elif stakeholder_type == "security":
            # Security-focused findings
            security_findings = [
                f.to_dict() for section in self.sections.values()
                for f in section.findings if f.category in ["security", "compliance"]
            ]
            stakeholder_report["security_findings"] = security_findings[:10]  # Limit to top 10

        elif stakeholder_type == "business":
            # Business impact focus
            stakeholder_report["business_impact_assessment"] = self._get_business_impact_summary()
            stakeholder_report["timeline_risks"] = self.get_overdue_findings()

        elif stakeholder_type == "product":
            # Product delivery focus
            theme_report = self._get_theme_layout()
            stakeholder_report["release_readiness"] = theme_report.get("release_readiness", "unknown")
            stakeholder_report["blocking_issues"] = [f.to_dict() for f in self.get_critical_findings()]

        return stakeholder_report

    def _get_technical_metrics(self) -> Dict[str, Any]:
        """Get technical metrics for engineering reporting"""
        metrics = {
            "total_sections": len(self.sections),
            "sections_with_findings": sum(1 for s in self.sections.values() if s.findings),
            "findings_by_status": {},
            "average_age_days": 0
        }

        # Calculate findings by status
        status_counts = {}
        total_age = 0
        finding_count = 0

        for section in self.sections.values():
            for finding in section.findings:
                finding_count += 1
                status_counts[finding.status] = status_counts.get(finding.status, 0) + 1
                total_age += finding.get_age_days()

        metrics["findings_by_status"] = status_counts
        if finding_count > 0:
            metrics["average_age_days"] = total_age / finding_count

        return metrics

    def _get_business_impact_summary(self) -> Dict[str, Any]:
        """Get business impact summary"""
        return {
            "can_proceed_to_production": self.overall_score >= 90.0,
            "estimated_additional_effort": self._estimate_remaining_effort(),
            "major_risks": [f.title for f in self.get_critical_findings()],
            "time_to_resolution": self._estimate_resolution_time()
        }

    def _estimate_remaining_effort(self) -> str:
        """Estimate remaining effort needed"""
        critical_count = len(self.get_critical_findings())
        if critical_count > 5:
            return "Substantial effort required (>1 month)"
        elif critical_count > 2:
            return "Moderate effort required (2-4 weeks)"
        elif critical_count > 0:
            return "Minimal effort required (1-2 weeks)"
        else:
            return "Ready for production"

    def _estimate_resolution_time(self) -> str:
        """Estimate time to resolve outstanding issues"""
        overdue_count = len(self.get_overdue_findings())
        if overdue_count > 3:
            return "Immediate attention required"
        elif overdue_count > 1:
            return "Address within 1-2 days"
        elif overdue_count > 0:
            return "Address within 1 week"
        else:
            return "All issues within timeline"

    def _get_theme_layout(self) -> Dict[str, Any]:
        """Get theme-specific insights for product reporting"""
        return {
            "product_readiness_score": min(100.0, self.overall_score + 10.0),  # Slight bonus for product focus
            "customer_impact_assessment": self._get_customer_impact_assessment(),
            "feature_completion_tracking": {
                "validation_complete": any(s.section_name == ReportSection.VALIDATION_PROTOCOL
                                        and s.overall_status == ComplianceStatus.COMPLIANT
                                        for s in self.sections.values()),
                "performance_meets_targets": any(s.section_name == ReportSection.PERFORMANCE_METRICS
                                              and s.score_percentage >= 85.0
                                              for s in self.sections.values())
            },
            "go_to_market_rating": self._calculate_go_to_market_rating()
        }

    def _get_customer_impact_assessment(self) -> str:
        """Assess customer impact level"""
        critical_findings = self.get_critical_findings()
        if any("user" in f.impact_description.lower() or "customer" in f.impact_description.lower()
               for f in critical_findings):
            return "High customer impact - requires immediate remediation"
        elif self.overall_score >= 80.0:
            return "Low customer impact - minor user-facing issues"
        else:
            return "Medium customer impact - some user experience concerns"

    def _calculate_go_to_market_rating(self) -> str:
        """Calculate go-to-market readiness rating"""
        validation_score = 0
        security_score = 0

        # Check key validation components
        for section in self.sections.values():
            if section.section_name == ReportSection.VALIDATION_PROTOCOL:
                validation_score = section.score_percentage
            elif section.section_name == ReportSection.SECURITY_SCANNING:
                security_score = section.score_percentage

        combined_score = (self.overall_score + validation_score + security_score) / 3

        if combined_score >= 90.0:
            return "Launch Ready"
        elif combined_score >= 75.0:
            return "Launch Probable"
        elif combined_score >= 60.0:
            return "Launch With Caution"
        else:
            return "Not Launch Ready"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_title": self.report_title,
            "deliverable_name": self.deliverable_name,
            "environment": self.environment,
            "scope_description": self.scope_description,
            "assessor": self.assessor,
            "report_period_start": self.report_period_start.isoformat(),
            "report_period_end": self.report_period_end.isoformat(),
            "sections": {k.value: v.to_dict() for k, v in self.sections.items()},
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "critical_actions": self.critical_actions,
            "reviewed_by": self.reviewed_by,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "version": self.version,
            "critical_findings_count": len(self.get_critical_findings()),
            "overdue_findings_count": len(self.get_overdue_findings()),
            "finding_summary_by_category": self.get_finding_summary_by_category()
        }
