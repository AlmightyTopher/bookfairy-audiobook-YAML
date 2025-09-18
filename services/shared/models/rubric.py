"""
Ranking Rubric Model
Severity/Ease ranking system for governance and risk assessment
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SeverityLevel(Enum):
    """Severity levels from Blocker to Low"""
    BLOCKER = "blocker"      # System cannot function
    HIGH = "high"           # Major impact on system operation
    MEDIUM = "medium"       # Degrades quality or reliability
    LOW = "low"            # Minor issues, future polish


class EaseLevel(Enum):
    """Ease of implementation levels"""
    EASY = "easy"          # <30 minutes, straightforward
    MODERATE = "moderate"  # Hours, moderate complexity
    HARD = "hard"          # Days+, external dependencies, complex


@dataclass
class RankingCriteria:
    """Criteria for ranking items using severity/ease matrix"""

    criteria_name: str

    # Impact assessment
    functional_impact: str = ""         # What functionality is affected?
    user_impact: str = ""              # Impact on end users
    business_impact: str = ""          # Business implications

    # Technical factors
    technical_complexity: str = ""     # How technically challenging?
    dependencies: List[str] = field(default_factory=list)  # What depends on this?

    # Evidence and examples
    examples: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)

    # Scoring weights
    impact_weight: float = 1.0      # 0.0 to 2.0, how much this criteria affects severity
    ease_weight: float = 1.0        # 0.0 to 2.0, how much this criteria affects ease


@dataclass
class SeverityClassification:
    """Result of severity classification with reasoning"""

    classification: SeverityLevel

    # Assessment details
    impact_assessment: str
    functional_impact: str
    user_impact: str

    # Supporting criteria
    criteria_applied: List[RankingCriteria] = field(default_factory=list)

    # Confidence and reasoning
    confidence_score: float = 0.0     # 0.0 to 1.0
    reasoning: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Timestamp
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    assessor: Optional[str] = None


@dataclass
class EaseClassification:
    """Result of ease classification with reasoning"""

    classification: EaseLevel

    # Assessment details
    effort_estimation: str
    complexity_factors: List[str] = field(default_factory=list)
    dependencies_needed: List[str] = field(default_factory=list)

    # Supporting criteria
    criteria_applied: List[RankingCriteria] = field(default_factory=list)

    # Confidence and reasoning
    confidence_score: float = 0.0     # 0.0 to 1.0
    reasoning: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Estimated metrics
    estimated_hours: float = 0.0
    estimated_developers: int = 1

    # Timestamp
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    assessor: Optional[str] = None


@dataclass
class CombinedRanking:
    """Combined severity and ease ranking with prioritization"""

    # Individual classifications
    severity: SeverityClassification
    ease: EaseClassification

    # Combined prioritization score
    prioritization_score: float = 0.0  # Calculated based on matrix

    # Matrix positioning
    priority_category: str = ""       # e.g., "Critical Fix Now", "Future Enhancement"

    # Recommendations
    recommended_action: str = ""
    timeline_suggestion: str = ""
    risk_acceptance_eligible: bool = False

    # Context
    assessed_item: str = ""          # What was assessed
    assessment_context: str = ""     # Why this assessment was made

    # Metadata
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    assessor: Optional[str] = None

    def __post_init__(self):
        """Calculate prioritization based on severity and ease"""
        self._calculate_prioritization()
        self._determine_recommendations()

    def _calculate_prioritization(self):
        """Calculate prioritization score using severity x ease matrix"""

        # Severity scores: Blocker=10, High=7, Medium=4, Low=1
        severity_scores = {
            SeverityLevel.BLOCKER: 10,
            SeverityLevel.HIGH: 7,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 1
        }

        # Ease scores (lower is harder to implement): Easy=10, Moderate=5, Hard=1
        ease_scores = {
            EaseLevel.EASY: 10,
            EaseLevel.MODERATE: 5,
            EaseLevel.HARD: 1
        }

        severity_score = severity_scores.get(self.severity.classification, 5)
        ease_score = ease_scores.get(self.ease.classification, 5)

        # Combined formula: severity strongly weighted, ease as modifier
        self.prioritization_score = severity_score * 10 + (ease_score - 5) * 2

    def _determine_recommendations(self):
        """Determine recommendations based on matrix position"""

        # Critical fixes (Blocker + any ease)
        if self.severity.classification == SeverityLevel.BLOCKER:
            if self.ease.classification == EaseLevel.EASY:
                self.priority_category = "Critical Fix Now"
                self.recommended_action = "Drop everything and fix immediately"
                self.timeline_suggestion = "< 4 hours"
            elif self.ease.classification == EaseLevel.MODERATE:
                self.priority_category = "Blocker Fix"
                self.recommended_action = "Schedule for immediate sprint priority"
                self.timeline_suggestion = "< 24 hours"
            else:  # HARD
                self.priority_category = "Blocker - Dedicated Effort"
                self.recommended_action = "Allocate dedicated resources to fix"
                self.timeline_suggestion = "2-5 days"

        # High priority issues
        elif self.severity.classification == SeverityLevel.HIGH:
            if self.ease.classification == EaseLevel.EASY:
                self.priority_category = "High Priority Fix"
                self.recommended_action = "Include in current sprint priority"
                self.timeline_suggestion = "< 12 hours"
            elif self.ease.classification == EaseLevel.MODERATE:
                self.priority_category = "High Priority - Plan"
                self.recommended_action = "Plan for next sprint"
                self.timeline_suggestion = "1-2 days"
            else:  # HARD
                self.priority_category = "High Priority - Assess Risk"
                self.recommended_action = "Evaluate risk vs. effort"
                self.timeline_suggestion = "1-3 days"

        # Medium priority issues (risk acceptance candidates)
        elif self.severity.classification == SeverityLevel.MEDIUM:
            if self.ease.classification == EaseLevel.EASY:
                self.priority_category = "Medium - Quick Win"
                self.recommended_action = "Consider as quick improvement"
                self.timeline_suggestion = "Next sprint"
                self.risk_acceptance_eligible = True
            elif self.ease.classification == EaseLevel.MODERATE:
                self.priority_category = "Medium - Opportunity"
                self.recommended_action = "Include in sprint if capacity allows"
                self.timeline_suggestion = "1-2 weeks"
                self.risk_acceptance_eligible = True
            else:  # HARD
                self.priority_category = "Medium - Risk Assessment Required"
                self.recommended_action = "Document as risk with mitigation plan"
                self.timeline_suggestion = "2-4 weeks"
                self.risk_acceptance_eligible = True

        # Low priority issues (usually not urgent)
        else:  # LOW
            self.priority_category = "Low Priority"
            self.recommended_action = "Address during future polish/cleanup phase"
            self.timeline_suggestion = "Future releases"
            self.risk_acceptance_eligible = True


class RankingRubric:
    """Complete severity/ease ranking rubric system"""

    def __init__(self):
        self.severity_criteria: Dict[str, RankingCriteria] = {}
        self.ease_criteria: Dict[str, RankingCriteria] = {}
        self.assessment_history: List[CombinedRanking] = []

        # Initialize default criteria
        self._initialize_default_criteria()

    def _initialize_default_criteria(self):
        """Initialize default ranking criteria"""

        # Severity criteria
        self.severity_criteria = {
            "functional_breakage": RankingCriteria(
                criteria_name="functional_breakage",
                functional_impact="Complete system or service inoperability",
                user_impact="Users cannot use affected functionality",
                business_impact="Potential revenue loss and trust damage",
                technical_complexity="Critical system function affected",
                examples=["Authentication failure", "Database outage", "Core API down"],
                evidence_sources=["Error logs", "User feedback", "System metrics"],
                impact_weight=2.0
            ),
            "data_integrity_risk": RankingCriteria(
                criteria_name="data_integrity_risk",
                functional_impact="Data stored or processed incorrectly",
                user_impact="User data may be compromised or lost",
                business_impact="Legal and compliance issues, data breach",
                technical_complexity="Affects data persistence and retrieval",
                examples=["Data corruption", "Incorrect calculations", "Security breaches"],
                evidence_sources=["Database logs", "Security scans", "User reports"],
                impact_weight=1.8
            ),
            "performance_degradation": RankingCriteria(
                criteria_name="performance_degradation",
                functional_impact="System response time significantly slower",
                user_impact="Poor user experience, frustration",
                business_impact="Work slowdown, potential user abandonment",
                technical_complexity="Performance optimization needed",
                examples=["Slow API responses", "Database query timeouts"],
                evidence_sources=["Performance monitoring", "User feedback"],
                impact_weight=1.5
            ),
            "user_experience_issue": RankingCriteria(
                criteria_name="user_experience_issue",
                functional_impact="UI/UX problems affecting usability",
                user_impact="Difficulty using the product",
                business_impact="User dissatisfaction and potential churn",
                technical_complexity="Frontend or design changes needed",
                examples=["Confusing interface", "Navigation problems"],
                evidence_sources=["User testing", "Analytics data"],
                impact_weight=1.2
            )
        }

        # Ease criteria
        self.ease_criteria = {
            "documentation_available": RankingCriteria(
                criteria_name="documentation_available",
                technical_complexity="Well-documented changes",
                dependencies=["API docs", "code documentation"],
                examples=["Well-documented API changes", "Clear code examples"],
                evidence_sources=["Documentation repository", "API specifications"],
                ease_weight=1.5
            ),
            "similar_patterns_exist": RankingCriteria(
                criteria_name="similar_patterns_exist",
                technical_complexity="Following existing code patterns",
                dependencies=["Existing codebase", "Code standards"],
                examples=["Adding to existing CRUD operations", "Following established architecture"],
                evidence_sources=["Code review", "Architecture documentation"],
                ease_weight=1.5
            ),
            "external_dependencies": RankingCriteria(
                criteria_name="external_dependencies",
                technical_complexity="Requires coordination with external teams/dependencies",
                dependencies=["Third-party libraries", "External services", "Cross-team coordination"],
                examples=["New library integration", "API contract changes"],
                evidence_sources=["Dependency graph", "Team schedules"],
                ease_weight=0.7  # Harder with external dependencies
            ),
            "testing_complexity": RankingCriteria(
                criteria_name="testing_complexity",
                technical_complexity="Test coverage and verification complexity",
                dependencies=["Test frameworks", "CI/CD pipeline", "Manual testing needs"],
                examples=["Requires manual testing", "Complex integration testing"],
                evidence_sources=["Test suite coverage", "Testing requirements"],
                ease_weight=0.8
            )
        }

    def classify_severity(self, description: str, impact_details: Dict[str, Any],
                         assessor: Optional[str] = None) -> SeverityClassification:
        """Classify severity using criteria matching"""

        # Analyze description against criteria to determine severity
        severity_score = self._analyze_impact(description.lower(), impact_details)

        # Map score to severity level
        if severity_score >= 8.0:
            severity = SeverityLevel.BLOCKER
            confidence = 0.9
        elif severity_score >= 6.0:
            severity = SeverityLevel.HIGH
            confidence = 0.8
        elif severity_score >= 4.0:
            severity = SeverityLevel.MEDIUM
            confidence = 0.7
        else:
            severity = SeverityLevel.LOW
            confidence = 0.6

        return SeverityClassification(
            classification=severity,
            impact_assessment=description,
            functional_impact=impact_details.get("functional_impact", "Unknown functional impact"),
            user_impact=impact_details.get("user_impact", "Unknown user impact"),
            confidence_score=confidence,
            reasoning=f"Automated severity classification based on {severity_score:.1f} impact score",
            evidence={"impact_score": severity_score, "analysis_details": impact_details},
            assessor=assessor
        )

    def classify_ease(self, description: str, effort_details: Dict[str, Any],
                     assessor: Optional[str] = None) -> EaseClassification:
        """Classify ease using criteria matching"""

        # Analyze description against criteria to determine ease
        ease_score = self._analyze_effort(description.lower(), effort_details)

        # Map score to ease level
        if ease_score >= 8.0:
            ease = EaseLevel.EASY
            confidence = 0.9
            estimated_hours = 0.5
        elif ease_score >= 6.0:
            ease = EaseLevel.MODERATE
            confidence = 0.75
            estimated_hours = 4.0
        else:
            ease = EaseLevel.HARD
            confidence = 0.7
            estimated_hours = 32.0

        return EaseClassification(
            classification=ease,
            effort_estimation=f"Estimated {estimated_hours} hours",
            complexity_factors=effort_details.get("complexity_factors", []),
            dependencies_needed=effort_details.get("dependencies", []),
            confidence_score=confidence,
            reasoning=f"Automated ease classification based on {ease_score:.1f} ease score",
            evidence={"ease_score": ease_score, "analysis_details": effort_details},
            estimated_hours=estimated_hours,
            assessor=assessor
        )

    def create_combined_ranking(self, description: str, context: str,
                               severity_details: Optional[Dict[str, Any]] = None,
                               ease_details: Optional[Dict[str, Any]] = None,
                               assessor: Optional[str] = None) -> CombinedRanking:
        """Create complete severity/ease combined ranking"""

        # Default details if not provided
        if severity_details is None:
            severity_details = {"functional_impact": "standard_impact", "user_impact": "minor_disruption"}

        if ease_details is None:
            ease_details = {"complexity_factors": ["standard_development"], "dependencies": []}

        # Classify severity and ease
        severity = self.classify_severity(description, severity_details, assessor)
        ease = self.classify_ease(description, ease_details, assessor)

        # Create combined ranking
        ranking = CombinedRanking(
            severity=severity,
            ease=ease,
            assessed_item=description,
            assessment_context=context,
            assessor=assessor
        )

        # Record in history
        self.assessment_history.append(ranking)

        return ranking

    def _analyze_impact(self, description: str, details: Dict[str, Any]) -> float:
        """Analyze description and details to determine severity score"""
        score = 0.0

        # Check severity criteria
        for criteria_name, criteria in self.severity_criteria.items():
            weight = criteria.impact_weight

            # Check if description matches criteria examples
            for example in criteria.examples:
                if example.lower() in description:
                    score += weight * 1.5
                    break

            # Check impact details
            functional_match = details.get("functional_impact", "").lower()
            if criteria.functional_impact.lower() in functional_match:
                score += weight

        return min(10.0, score)  # Cap at 10.0

    def _analyze_effort(self, description: str, details: Dict[str, Any]) -> float:
        """Analyze description and details to determine ease score"""
        score = 0.0

        # Check ease criteria
        for criteria_name, criteria in self.ease_criteria.items():
            weight = criteria.ease_weight

            # Check if description matches criteria examples
            for example in criteria.examples:
                if example.lower() in description:
                    score += weight * 1.5
                    break

            # Check complexity details
            complexity_match = " ".join(details.get("complexity_factors", [])).lower()
            if any(example.lower() in complexity_match for example in criteria.examples):
                score += weight * 0.8

        return min(10.0, score)  # Cap at 10.0

    def get_priority_queue(self, limit: Optional[int] = None) -> List[CombinedRanking]:
        """Get ranking history sorted by priority score"""
        sorted_rankings = sorted(
            self.assessment_history,
            key=lambda r: r.prioritization_score,
            reverse=True  # Highest score first
        )
        return sorted_rankings[:limit] if limit else sorted_rankings

    def get_category_breakdown(self) -> Dict[str, List[CombinedRanking]]:
        """Break down rankings by priority category"""
        categories = {}
        for ranking in self.assessment_history:
            category = ranking.priority_category
            if category not in categories:
                categories[category] = []
            categories[category].append(ranking)

        return categories
