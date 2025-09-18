#!/usr/bin/env python3
"""
Governance Compliance Engine for BookFairy
Implements comprehensive audit lens application, compliance reporting, and governance validation
Based on data-model.md specification and integration tests
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
services_path = os.path.join(project_root, "services")
sys.path.insert(0, services_path)

from services.shared.models.governance import (
    AuditLensFramework, AuditLens, AuditFinding, AuditSeverity,
    UniversalAuditLens, LensConfiguration
)
from services.shared.models.health import HealthMonitorRegistry
from services.shared.models.workflow import WorkflowRegistry
from services.shared.models.container import DockerContainerRegistry
from services.shared.models.compliance import (
    GovernanceComplianceReport, ComplianceStatus, ReportSection, ComplianceFinding, ComplianceSection
)
from services.shared.models.rubric import ScoringRubric, SeverityLevel, EasinessLevel
from services.shared.models.risks import RisksTable
from services.shared.models.validation import ValidationProtocolRegistry


class GovernanceComplianceEngine:
    """Comprehensive governance and compliance engine with universal audit lenses"""

    def __init__(self):
        self.audit_framework = AuditLensFramework()
        self.health_registry = HealthMonitorRegistry()
        self.workflow_registry = WorkflowRegistry()
        self.container_registry = DockerContainerRegistry()

        # Governance registries
        self.compliance_reports: Dict[str, GovernanceComplianceReport] = {}
        self.risks_table = RisksTable(table_id="", name="BookFairy Governance Risks")
        self.scoring_rubric = ScoringRubric()
        self.validation_registry = ValidationProtocolRegistry()

        # Audit lens configurations
        self.lens_configurations: Dict[AuditLens, LensConfiguration] = {}
        self.active_audits: Dict[str, List[AuditFinding]] = {}

        print("Governance Compliance Engine initialized with Universal Audit Lens framework")

    def configure_audit_lenses(self):
        """Configure all 13 Universal Audit Lenses with their specific rules"""

        lens_configs = [
            # 1. Safety & Security Lens
            {
                "lens": AuditLens.SAFETY_SECURITY,
                "name": "Safety & Security",
                "description": "Audits all security aspects and potential vulnerabilities",
                "rules": self._get_security_rules()
            },
            # 2. Observability & Feedback Lens
            {
                "lens": AuditLens.OBSERVABILITY_FEEDBACK,
                "name": "Observability & Feedback",
                "description": "Ensures comprehensive monitoring and observability",
                "rules": self._get_observability_rules()
            },
            # 3. Performance & Efficiency Lens
            {
                "lens": AuditLens.PERFORMANCE_EFFICIENCY,
                "name": "Performance & Efficiency",
                "description": "Audits system performance and resource efficiency",
                "rules": self._get_performance_rules()
            },
            # 4. Scalability & Growth Lens
            {
                "lens": AuditLens.SCALABILITY_GROWTH,
                "name": "Scalability & Growth",
                "description": "Ensures system can handle growth and scale",
                "rules": self._get_scalability_rules()
            },
            # 5. Reliability & Continuity Lens
            {
                "lens": AuditLens.RELIABILITY_CONTINUITY,
                "name": "Reliability & Continuity",
                "description": "Audits system reliability and business continuity",
                "rules": self._get_reliability_rules()
            },
            # 6. Communication & Clarity Lens
            {
                "lens": AuditLens.COMMUNICATION_CLARITY,
                "name": "Communication & Clarity",
                "description": "Ensures clear communication and documentation",
                "rules": self._get_communication_rules()
            },
            # 7. Ethics & Compliance Lens
            {
                "lens": AuditLens.ETHICS_COMPLIANCE,
                "name": "Ethics & Compliance",
                "description": "Audits ethical considerations and regulatory compliance",
                "rules": self._get_ethics_rules()
            },
            # 8. Configuration & Management Lens
            {
                "lens": AuditLens.CONFIGURATION_MANAGEMENT,
                "name": "Configuration & Management",
                "description": "Audits configuration management and system organization",
                "rules": self._get_configuration_rules()
            },
            # 9. Data Quality & Integrity Lens
            {
                "lens": AuditLens.DATA_QUALITY_INTEGRITY,
                "name": "Data Quality & Integrity",
                "description": "Ensures data quality and integrity throughout the system",
                "rules": self._get_data_quality_rules()
            },
            # 10. Cost Optimization Lens
            {
                "lens": AuditLens.COST_OPTIMIZATION,
                "name": "Cost Optimization",
                "description": "Audits for cost efficiencies and optimization opportunities",
                "rules": self._get_cost_optimization_rules()
            },
            # 11. Automated Decisions Lens
            {
                "lens": AuditLens.AUTOMATED_DECISIONS,
                "name": "Automated Decisions",
                "description": "Audits automated decision-making processes",
                "rules": self._get_automated_decisions_rules()
            },
            # 12. Human Integration Lens
            {
                "lens": AuditLens.HUMAN_INTEGRATION,
                "name": "Human Integration",
                "description": "Audits human-machine interactions and usability",
                "rules": self._get_human_integration_rules()
            },
            # 13. Future-Proofing Lens
            {
                "lens": AuditLens.FUTURE_PROOFING,
                "name": "Future Proofing",
                "description": "Ensures system is prepared for future requirements",
                "rules": self._get_future_proofing_rules()
            }
        ]

        # Apply configurations
        for config_data in lens_configs:
            config = LensConfiguration(
                lens_type=config_data["lens"],
                name=config_data["name"],
                description=config_data["description"],
                rules=config_data["rules"],
                enabled=True
            )
            self.lens_configurations[config_data["lens"]] = config

        print(f"Configured {len(self.lens_configurations)} Universal Audit Lenses")

    def _get_security_rules(self) -> List[str]:
        return [
            "Check for authentication and authorization mechanisms",
            "Validate data encryption at rest and in transit",
            "Audit container security configurations",
            "Verify dependency vulnerability scanning",
            "Check API endpoint security protections",
            "Validate user session management",
            "Audit rate limiting implementations",
            "Verify sensitive data handling protections"
        ]

    def _get_observability_rules(self) -> List[str]:
        return [
            "Validate comprehensive health check endpoints",
            "Check continuous monitoring implementations",
            "Audit logging and alerting configurations",
            "Verify performance metrics collection",
            "Check error handling and reporting",
            "Validate audit trail completeness",
            "Ensure observability at all service layers",
            "Confirm operational visibility coverage"
        ]

    def _get_performance_rules(self) -> List[str]:
        return [
            "Audit response time targets",
            "Check resource utilization efficiency",
            "Validate caching strategy effectiveness",
            "Monitor concurrent request handling",
            "Check database query performance",
            "Validate memory and CPU usage",
            "Audit network latency patterns",
            "Verify scaling performance"
        ]

    def _get_scalability_rules(self) -> List[str]:
        return [
            "Check horizontal scaling capabilities",
            "Validate load balancing configurations",
            "Audit resource allocation strategies",
            "Check database scaling mechanisms",
            "Validate distributed caching",
            "Audit microservices architecture",
            "Check service discovery and registration",
            "Validate container orchestration"
        ]

    def _get_reliability_rules(self) -> List[str]:
        return [
            "Audit error handling patterns",
            "Validate retry mechanism implementations",
            "Check circuit breaker patterns",
            "Audit backup and recovery procedures",
            "Validate data consistency mechanisms",
            "Check system redundancy",
            "Audit disaster recovery capabilities",
            "Validate service health monitoring"
        ]

    def _get_communication_rules(self) -> List[str]:
        return [
            "Audit API documentation completeness",
            "Validate error message clarity",
            "Check user interface messaging",
            "Audit system status communications",
            "Validate audit trail readability",
            "Check stakeholder reporting clarity",
            "Audit system interaction patterns",
            "Validate user feedback mechanisms"
        ]

    def _get_ethics_rules(self) -> List[str]:
        return [
            "Audit bias in AI recommendations",
            "Validate data privacy protections",
            "Check content moderation mechanisms",
            "Audit user consent handling",
            "Validate ethical AI decision-making",
            "Check transparent algorithm explanations",
            "Audit user control mechanisms",
            "Validate governance oversight"
        ]

    def _get_configuration_rules(self) -> List[str]:
        return [
            "Audit configuration management processes",
            "Validate secret management practices",
            "Check environment variable handling",
            "Audit configuration version control",
            "Validate configuration change procedures",
            "Check configuration audit trails",
            "Audit system organization patterns",
            "Validate configuration consistency"
        ]

    def _get_data_quality_rules(self) -> List[str]:
        return [
            "Audit data validation patterns",
            "Validate data integrity mechanisms",
            "Check data consistency validation",
            "Audit data transformation accuracy",
            "Validate input sanitization",
            "Check data backup integrity",
            "Audit data migration accuracy",
            "Validate data quality monitoring"
        ]

    def _get_cost_optimization_rules(self) -> List[str]:
        return [
            "Audit resource utilization costs",
            "Check compute resource efficiency",
            "Validate storage cost optimization",
            "Audit network cost patterns",
            "Check unused resource cleanup",
            "Validate licensing cost effectiveness",
            "Audit third-party service costs",
            "Check operational cost monitoring"
        ]

    def _get_automated_decisions_rules(self) -> List[str]:
        return [
            "Audit automated decision accuracy",
            "Validate decision-making transparency",
            "Check automated process robustness",
            "Audit decision fallback mechanisms",
            "Validate human override capabilities",
            "Check automated decision monitoring",
            "Audit decision-making boundary conditions",
            "Validate decision audit logging"
        ]

    def _get_human_integration_rules(self) -> List[str]:
        return [
            "Audit user interface usability",
            "Validate human-AI interaction patterns",
            "Check user feedback mechanisms",
            "Audit learning curve minimization",
            "Validate error recoverability",
            "Check accessibility compliance",
            "Audit user control mechanisms",
            "Validate user empowerment features"
        ]

    def _get_future_proofing_rules(self) -> List[str]:
        return [
            "Audit technology stack currency",
            "Validate architectural scalability",
            "Check modular design patterns",
            "Audit deprecation preparation",
            "Validate vendor dependency management",
            "Check industry trend alignment",
            "Audit technical debt monitoring",
            "Validate innovation capacity"
        ]

    async def conduct_comprehensive_audit(self, target_system: str = "bookfairy") -> List[AuditFinding]:
        """Conduct comprehensive audit using all 13 Universal Audit Lenses"""

        audit_id = f"audit_{target_system}_{int(datetime.utcnow().timestamp())}"
        all_findings: List[AuditFinding] = []

        print(f"🔍 Conducting comprehensive audit: {audit_id}")

        # Apply each configured audit lens
        for lens_type, config in self.lens_configurations.items():
            if not config.enabled:
                continue

            print(f"  Applying {config.name} lens...")

            try:
                # Apply lens to collect audit data
                audit_target = self._collect_audit_data_for_lens(lens_type, target_system)
                lens_findings = self.audit_framework.apply_lens(lens_type, audit_target, {"audit_id": audit_id})

                # Enhance findings with lens-specific context
                for finding in lens_findings:
                    finding.tags.append(f"lens:{lens_type.name}")
                    finding.audit_id = audit_id

                all_findings.extend(lens_findings)
                print(f"    Found {len(lens_findings)} findings")

            except Exception as e:
                print(f"    Error in {config.name} lens: {e}")
                # Create error finding
                error_finding = AuditFinding(
                    finding_id=f"error_{audit_id}_{lens_type.name}",
                    title=f"Audit Error in {config.name}",
                    description=f"Unable to complete audit lens application: {str(e)}",
                    severity=AuditSeverity.MEDIUM,
                    category="audit_error",
                    lens_type=lens_type,
                    audit_id=audit_id
                )
                all_findings.append(error_finding)

        # Store audit results
        self.active_audits[audit_id] = all_findings

        print(f"✅ Comprehensive audit completed: {len(all_findings)} total findings")
        return all_findings

    def _collect_audit_data_for_lens(self, lens_type: AuditLens, target_system: str) -> Dict[str, Any]:
        """Collect audit data relevant to a specific lens"""

        audit_data = {
            "target_system": target_system,
            "audit_timestamp": datetime.utcnow().isoformat(),
            "lens_type": lens_type.name
        }

        if lens_type == AuditLens.SAFETY_SECURITY:
            audit_data.update(self._collect_security_audit_data())
        elif lens_type == AuditLens.OBSERVABILITY_FEEDBACK:
            audit_data.update(self._collect_observability_audit_data())
        elif lens_type == AuditLens.PERFORMANCE_EFFICIENCY:
            audit_data.update(self._collect_performance_audit_data())
        elif lens_type == AuditLens.SCALABILITY_GROWTH:
            audit_data.update(self._collect_scalability_audit_data())
        elif lens_type == AuditLens.RELIABILITY_CONTINUITY:
            audit_data.update(self._collect_reliability_audit_data())
        elif lens_type == AuditLens.COMMUNICATION_CLARITY:
            audit_data.update(self._collect_communication_audit_data())
        elif lens_type == AuditLens.ETHICS_COMPLIANCE:
            audit_data.update(self._collect_ethics_audit_data())
        elif lens_type == AuditLens.CONFIGURATION_MANAGEMENT:
            audit_data.update(self._collect_configuration_audit_data())
        elif lens_type == AuditLens.DATA_QUALITY_INTEGRITY:
            audit_data.update(self._collect_data_quality_audit_data())
        elif lens_type == AuditLens.COST_OPTIMIZATION:
            audit_data.update(self._collect_cost_optimization_audit_data())
        elif lens_type == AuditLens.AUTOMATED_DECISIONS:
            audit_data.update(self._collect_automated_decisions_audit_data())
        elif lens_type == AuditLens.HUMAN_INTEGRATION:
            audit_data.update(self._collect_human_integration_audit_data())
        elif lens_type == AuditLens.FUTURE_PROOFING:
            audit_data.update(self._collect_future_proofing_audit_data())

        return audit_data

    def _collect_security_audit_data(self) -> Dict[str, Any]:
        """Collect security-relevant audit data"""
        return {
            "services_count": len(self.health_registry.get_service_health_summaries()),
            "enabled_audits": len(self.active_audits),
            "recent_findings": len([f for audit in self.active_audits.values() for f in audit])
        }

    def _collect_observability_audit_data(self) -> Dict[str, Any]:
        """Collect observability-relevant audit data"""
        health_summaries = self.health_registry.get_service_health_summaries()
        return {
            "services_monitored": len(health_summaries),
            "healthy_services": len([s for s in health_summaries.values() if s.overall_status == "healthy"]),
            "workflows_tracked": len(self.workflow_registry.workflows),
            "audit_trails": len(self.active_audits)
        }

    def _collect_performance_audit_data(self) -> Dict[str, Any]:
        """Collect performance-relevant audit data"""
        workflows = list(self.workflow_registry.workflows.values())
        return {
            "total_workflows": len(workflows),
            "completed_workflows": len([w for w in workflows if w.status.value == "completed"]),
            "failed_workflows": len([w for w in workflows if w.status.value == "failed"]),
            "avg_execution_time": sum([w.total_execution_time_ms for w in workflows]) / len(workflows) if workflows else 0
        }

    # Implement remaining audit data collection methods...
    def _collect_scalability_audit_data(self) -> Dict[str, Any]:
        return {"services_count": len(self.health_registry.get_service_health_summaries())}

    def _collect_reliability_audit_data(self) -> Dict[str, Any]:
        workflows = list(self.workflow_registry.workflows.values())
        return {
            "workflow_success_rate": len([w for w in workflows if w.status.value == "completed"]) / len(workflows) if workflows else 0,
            "services_health_rate": len([h for h in self.health_registry.get_service_health_summaries().values() if h.overall_status == "healthy"]) / len(self.health_registry.get_service_health_summaries()) if self.health_registry.get_service_health_summaries() else 0
        }

    def _collect_communication_audit_data(self) -> Dict[str, Any]:
        return {"audits_conducted": len(self.active_audits)}

    def _collect_ethics_audit_data(self) -> Dict[str, Any]:
        return {"workflows_executed": len(self.workflow_registry.workflows)}

    def _collect_configuration_audit_data(self) -> Dict[str, Any]:
        return {"containers_registered": len(self.container_registry.containers)}

    def _collect_data_quality_audit_data(self) -> Dict[str, Any]:
        return {"data_validation_operations": 0}  # Placeholder

    def _collect_cost_optimization_audit_data(self) -> Dict[str, Any]:
        return {"services_operated": len(self.health_registry.get_service_health_summaries())}

    def _collect_automated_decisions_audit_data(self) -> Dict[str, Any]:
        return {"automated_processes": len(self.lens_configurations)}  # Placeholder

    def _collect_human_integration_audit_data(self) -> Dict[str, Any]:
        return {"user_interactions": 0}  # Would count from Discord bot data

    def _collect_future_proofing_audit_data(self) -> Dict[str, Any]:
        return {"technology_stack_currency": "current"}

    def generate_compliance_report(self, audit_findings: List[AuditFinding], assessor: str = "GovernanceEngine") -> GovernanceComplianceReport:
        """Generate comprehensive compliance report from audit findings"""

        report = GovernanceComplianceReport(
            report_id="",
            report_title=f"Universal Audit Lens Compliance Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
            deliverable_name="BookFairy Docker Orchestration Platform",
            assessor=assessor
        )

        # Add findings to appropriate sections
        audit_lens_section = report.sections[ReportSection.AUDIT_LENS_RESULTS]
        risk_section = report.sections[ReportSection.RISK_ASSESSMENT]
        perf_section = report.sections[ReportSection.PERFORMANCE_METRICS]
        sec_section = report.sections[ReportSection.SECURITY_SCANNING]

        # Categorize findings
        for finding in audit_findings:
            compliance_finding = ComplianceFinding(
                finding_id=finding.finding_id,
                title=finding.title,
                description=finding.description,
                severity_level="blocker" if finding.severity == AuditSeverity.BLOCKER else
                              "critical" if finding.severity == AuditSeverity.CRITICAL else
                              "major" if finding.severity == AuditSeverity.MAJOR else
                              "minor" if finding.severity == AuditSeverity.MINOR else "info",
                category=f"audit_lentgen" + finding.lens_type.name.lower()
            )

            # Add to audit lens section
            audit_lens_section.findings.append(compliance_finding)

            # Also add to specific sections based on category
            if "security" in finding.category or "safety" in finding.category:
                sec_section.findings.append(compliance_finding)
            elif "performance" in finding.category:
                perf_section.findings.append(compliance_finding)
            elif "risk" in finding.category:
                risk_section.findings.append(compliance_finding)

        # Calculate compliance scores for all sections
        for section_name, section in report.sections.items():
            section.calculate_section_score()

        # Calculate overall compliance score
        report.calculate_overall_score()

        # Generate executive summary
        report.generate_executive_summary()

        # Store report
        self.compliance_reports[report.report_id] = report

        print(f"📊 Compliance report generated: {report.report_id} - Score: {report.overall_score:.1f}%")
        return report

    def assess_termination_criteria(self) -> Dict[str, Any]:
        """Assess project termination criteria against current system state"""

        assessment = {
            "assessment_date": datetime.utcnow().isoformat(),
            "trigger_termination_criteria": [],
            "mitigation_required_criteria": [],
            "satisfactory_criteria": [],
            "overall_termination_recommended": False
        }

        # Criterion 1: Security breaches (BLOCKER severity findings)
        critical_findings = []
        for audit in self.active_audits.values():
            critical_findings.extend([f for f in audit if f.severity == AuditSeverity.BLOCKER])

        if len(critical_findings) > 0:
            assessment["trigger_termination_criteria"].append({
                "criterion": "Critical Security Violations",
                "details": f"{len(critical_findings)} blocker-level security findings detected",
                "severity": "TERMINATION"
            })

        # Criterion 2: Complete system failure
        health_status = self.health_registry.get_system_health_overview()
        if health_status["healthy_services"] == 0:
            assessment["trigger_termination_criteria"].append({
                "criterion": "Complete System Failure",
                "details": f"No services are healthy ({health_status['healthy_services']}/{health_status['total_services']})",
                "severity": "TERMINATION"
            })

        # Criterion 3: Governance violations
        governance_violations = len([f for audit in self.active_audits.values()
                                   for f in audit if "governance" in f.category.lower() and f.severity in [AuditSeverity.BLOCKER, AuditSeverity.CRITICAL]])
        if governance_violations > 2:
            assessment["trigger_termination_criteria"].append({
                "criterion": "Critical Governance Violations",
                "details": f"{governance_violations} critical governance violations detected",
                "severity": "TERMINATION"
            })

        # Criterion 4: Performance degradation
        performance_violations = len([f for audit in self.active_audits.values()
                                    for f in audit if "performance" in f.category.lower() and f.severity == AuditSeverity.CRITICAL])
        if performance_violations > 5:
            assessment["mitigation_required_criteria"].append({
                "criterion": "Severe Performance Issues",
                "details": f"{performance_violations} critical performance issues require mitigation",
                "severity": "MITIGATION_REQUIRED"
            })

        # Criterion 5: Compliance score
        recent_report = max(self.compliance_reports.values(), key=lambda r: r.created_at) if self.compliance_reports else None
        if recent_report and recent_report.overall_score < 30.0:
            assessment["trigger_termination_criteria"].append({
                "criterion": "Critical Compliance Failure",
                "details": f"Overall compliance score: {recent_report.overall_score:.1f}% (below termination threshold)",
                "severity": "TERMINATION"
            })

        # Determine overall recommendation
        assessment["overall_termination_recommended"] = len(assessment["trigger_termination_criteria"]) > 0

        return assessment

    def get_governance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive governance dashboard"""

        # Collect system metrics
        system_health = self.health_registry.get_system_health_overview()

        # Collect workflow metrics
        workflows = list(self.workflow_registry.workflows.values())
        completed_workflows = [w for w in workflows if w.status.value == "completed"]
        failed_workflows = [w for w in workflows if w.status.value == "failed"]

        # Collect compliance metrics
        compliance_scores = [r.calculated_overall_score() for r in self.compliance_reports]

        # Collect risk metrics
        risk_scores = [risk.calculate_risk_score() for risk in self.risks_table.risks]

        return {
            "dashboard_generated": datetime.utcnow().isoformat(),
            "system_health": {
                "total_services": system_health["total_services"],
                "healthy_percentage": (system_health["healthy_services"] / system_health["total_services"] * 100) if system_health["total_services"] > 0 else 0,
                "total_services": system_health["total_services"],
                "healthy_services": system_health["healthy_services"],
                "unhealthy_services": system_health["unhealthy_services"]
            },
            "workflow_metrics": {
                "total_workflows": len(workflows),
                "completion_rate": len(completed_workflows) / len(workflows) * 100 if workflows else 0,
                "failure_rate": len(failed_workflows) / len(workflows) * 100 if workflows else 0,
                "avg_execution_time_ms": sum([w.total_execution_time_ms for w in workflows]) / len(workflows) if workflows else 0
            },
            "compliance_metrics": {
                "total_reports": len(self.compliance_reports),
                "latest_score": compliance_scores[-1] if compliance_scores else 0,
                "average_score": sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0,
                "audit_lenses_active": len(self.lens_configurations)
            },
            "risk_metrics": {
                "total_risks": len(risk_scores),
                "average_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
                "high_severity_risks": len([s for s in risk_scores if s > 6.0]),
                "critical_risks": len([s for s in risk_scores if s > 8.0])
            },
            "audit_findings": {
                "total_audits": len(self.active_audits),
                "total_findings": sum(len(findings) for findings in self.active_audits.values()),
                "blocker_findings": sum(len([f for f in findings if f.severity == AuditSeverity.BLOCKER]) for findings in self.active_audits.values()),
                "critical_findings": sum(len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) for findings in self.active_audits.values())
            }
        }


async def main():
    """Main governance compliance engine entry point"""

    engine = GovernanceComplianceEngine()
    engine.configure_audit_lenses()

    print("BookFairy Governance Compliance Engine started")
    print(f"Configured {len(engine.lens_configurations)} Universal Audit Lenses")

    # Conduct comprehensive audit
    print("\n🔍 Conducting comprehensive system audit...")
    audit_findings = await engine.conduct_comprehensive_audit()

    # Generate compliance report
    print("\n📊 Generating compliance report...")
    compliance_report = engine.generate_compliance_report(audit_findings)

    # Assess termination criteria
    print("\n⚖️ Assessing termination criteria...")
    termination_assessment = engine.assess_termination_criteria()

    # Generate governance dashboard
    print("\n📈 Generating governance dashboard...")
    dashboard = engine.get_governance_dashboard()

    # Display results
    print("\n" + "="*80)
    print("🎯 GOVERNANCE COMPLIANCE ENGINE RESULTS")
    print("="*80)

    print("Audits Conducted")
    print(f"  Universal Audit Lenses: {len(engine.lens_configurations)}")
    print(f"  Total Findings: {len(audit_findings)}")
    print(f"  Blocker Findings: {len([f for f in audit_findings if f.severity == AuditSeverity.BLOCKER])}")
    print(f"  Critical Findings: {len([f for f in audit_findings if f.severity == AuditSeverity.CRITICAL])}")

    print(f"\nCompliance Score: {compliance_report.overall_score:.1f}%")
    print(f"Status: {compliance_report.overall_status.value}")

    print(".1f")
    print(f"Healthy Services: {dashboard['system_health']['healthy_services']}/{dashboard['system_health']['total_services']}")

    print(".1f")
    print(f"Completed: {dashboard['workflow_metrics']['completion_rate']:.1f}%")

    print(f"\nTermination Assessment:")
    if termination_assessment["overall_termination_recommended"]:
        print("  ⚠️ TERMINATION RECOMMENDED")
        for criterion in termination_assessment["trigger_termination_criteria"]:
            print(f"  ❌ {criterion['criterion']}: {criterion['details']}")
    else:
        print("  ✅ TERMINATION NOT RECOMMENDED")

    print(".1f")

    print("\n🔄 Governance Compliance Engine monitoring and analysis complete")
    print("All Universal Audit Lenses have been applied to the BookFairy ecosystem")
    print("Compliance and governance assessment is ongoing...")

    # Keep engine running for continuous monitoring
    print("\n🎛️ Engine ready for continuous compliance monitoring...")
    try:
        while True:
            # Conduct periodic audits
            await asyncio.sleep(300)  # Audit every 5 minutes
            periodic_findings = await engine.conduct_comprehensive_audit("bookfairy-periodic")
            if periodic_findings:
                print(f"Periodic audit found {len(periodic_findings)} findings")
                # Update compliance report
                updated_report = engine.generate_compliance_report(periodic_findings)
    except KeyboardInterrupt:
        print("\n🛑 Governance Compliance Engine stopped by user")
    finally:
        print("🏁 Governance Compliance Engine shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
