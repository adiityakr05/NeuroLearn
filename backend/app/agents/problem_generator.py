"""
Problem Generator
=================
Implementation of the Problem Generator Element (Russell & Norvig learning agent architecture).
Responsible for:
- Formulating diagnostic problem probes and targeted practice challenges.
- Adapting question difficulty and Bloom's Taxonomy levels to student mastery.
- Supporting MCQ, True/False, Short Answer, and Conceptual/Application question types.
- Synthesizing practice recommendation candidates under agent_element="Problem Generator".
- Preventing duplicate question generation and handling insufficient context cleanly.
"""

from typing import List, Dict, Any, Optional
import uuid

from app.agents.base import BaseAgent
from app.agents.schemas import (
    StudentContext,
    TopicContext,
    AgentRecommendationCandidate,
)
from app.agents.problem_schemas import (
    GeneratedQuestion,
    DiagnosticProbeSet,
    ProblemGeneratorResult,
)


class ProblemGenerator(BaseAgent):
    """
    Problem Generator synthesizing targeted diagnostic questions across Bloom's Taxonomy.
    """

    def __init__(self) -> None:
        super().__init__(name="ProblemGenerator", element_role="Problem Generator")

    def run(
        self,
        context: StudentContext,
        target_topic_ids: Optional[List[str]] = None,
        max_questions_per_topic: int = 4,
        **kwargs,
    ) -> ProblemGeneratorResult:
        """
        Synthesizes diagnostic question sets for weak or selected topics.
        """
        if not context.topics:
            self.log_execution("No topics available in context.")
            return ProblemGeneratorResult(
                user_id=context.student.user_id,
                probes=[],
                recommendation_candidates=[],
                status="empty_topics",
            )

        # 1. Identify target weak topics (or use explicitly supplied target_topic_ids)
        target_topics = self.select_target_topics(context, target_topic_ids)
        if not target_topics:
            self.log_execution("No eligible topics for problem generation.")
            return ProblemGeneratorResult(
                user_id=context.student.user_id,
                probes=[],
                recommendation_candidates=[],
                status="insufficient_context",
            )

        probes: List[DiagnosticProbeSet] = []
        rec_candidates: List[AgentRecommendationCandidate] = []

        for topic in target_topics:
            bloom_level, diff = self.determine_bloom_and_difficulty(topic, context)
            questions = self.generate_questions_for_topic(
                topic=topic,
                bloom_level=bloom_level,
                difficulty=diff,
                max_count=max_questions_per_topic,
            )

            if questions:
                rationale = (
                    f"Diagnostic probe generated for {topic.name} ({diff} difficulty, "
                    f"{bloom_level} Bloom's level) to target current mastery ({topic.mastery_score:.1f}%)."
                )
                probe_set = DiagnosticProbeSet(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    target_bloom_level=bloom_level,
                    difficulty=diff,
                    questions=questions,
                    estimated_duration_minutes=len(questions) * 3,
                    diagnostic_rationale=rationale,
                )
                probes.append(probe_set)

                # Generate Recommendation Candidate under Problem Generator
                rec = AgentRecommendationCandidate(
                    subject_id=topic.subject_id,
                    topic_id=topic.id,
                    agent_element=self.element_role,
                    type="diagnostic_probe",
                    priority="high" if topic.mastery_score < 60.0 else "medium",
                    title=f"Diagnostic Challenge: {topic.name}",
                    reason_type="diagnostic_exploration",
                    reason_detail=rationale,
                    suggested_slot="Flexible",
                    estimated_duration_minutes=probe_set.estimated_duration_minutes,
                )
                rec_candidates.append(rec)

        self.log_execution(
            "Generated diagnostic probes",
            {"probe_count": len(probes), "total_questions": sum(len(p.questions) for p in probes)},
        )

        return ProblemGeneratorResult(
            user_id=context.student.user_id,
            probes=probes,
            recommendation_candidates=rec_candidates,
            status="success",
        )

    def select_target_topics(
        self,
        context: StudentContext,
        target_topic_ids: Optional[List[str]] = None,
    ) -> List[TopicContext]:
        """
        Selects candidate topics requiring diagnostic probing.
        Filters by low mastery (<70%) or lowest retention, or uses explicit target IDs.
        """
        if target_topic_ids:
            return [t for t in context.topics if t.id in target_topic_ids]

        # Prioritize topics with mastery < 75 or retention < 70
        candidates = [
            t for t in context.topics
            if t.mastery_score < 75.0 or t.retention_score < 70.0
        ]
        if not candidates:
            # Fallback to topic with lowest mastery
            candidates = sorted(context.topics, key=lambda t: t.mastery_score)[:2]
        return candidates[:3]  # Focus on top 3 candidates

    def determine_bloom_and_difficulty(
        self,
        topic: TopicContext,
        context: StudentContext,
    ) -> (str, str):
        """
        Maps topic mastery to appropriate Bloom's Taxonomy level and difficulty:
        - Mastery < 50%: Remember / Understand (Easy/Medium) - Foundational recall
        - 50% <= Mastery < 70%: Understand / Apply (Medium) - Conceptual application
        - 70% <= Mastery < 85%: Apply / Analyze (Medium/Hard) - Diagnostic probes
        - Mastery >= 85%: Evaluate / Create (Hard) - Frontier synthesis & evaluation
        """
        mastery = topic.mastery_score
        if mastery < 50.0:
            return "Remember", "Easy"
        elif mastery < 70.0:
            return "Understand", "Medium"
        elif mastery < 85.0:
            return "Apply", "Medium"
        elif mastery < 95.0:
            return "Analyze", "Hard"
        else:
            return "Evaluate", "Hard"

    def generate_questions_for_topic(
        self,
        topic: TopicContext,
        bloom_level: str,
        difficulty: str,
        max_count: int = 4,
    ) -> List[GeneratedQuestion]:
        """
        Synthesizes structured questions across supported types using deterministic templates.
        Guarantees unique IDs and prevents duplicate templates within the set.
        """
        questions: List[GeneratedQuestion] = []
        templates = self.get_templates_for_topic(topic, bloom_level, difficulty)

        for tmpl in templates[:max_count]:
            qid = f"gen-q-{topic.id[:6]}-{tmpl['type']}-{len(questions)+1}"
            q = GeneratedQuestion(
                id=qid,
                topic_id=topic.id,
                topic_name=topic.name,
                question_text=tmpl["text"],
                question_type=tmpl["type"],
                difficulty=difficulty,
                bloom_level=bloom_level,
                options=tmpl.get("options"),
                correct_answer=tmpl["answer"],
                explanation=tmpl["explanation"],
                learning_objective=tmpl["objective"],
            )
            questions.append(q)

        return questions

    def get_templates_for_topic(
        self,
        topic: TopicContext,
        bloom: str,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """
        Returns structured question templates tailored to the topic name, Bloom's level,
        and difficulty tier.
        """
        name = topic.name
        subj = topic.subject_name

        if bloom in ["Remember", "Understand"]:
            return [
                {
                    "type": "mcq",
                    "text": f"What is the foundational principle behind {name} in {subj}?",
                    "options": [
                        f"Core conceptual definition and properties of {name}",
                        f"Unrelated algorithmic transformation in external libraries",
                        f"Arbitrary heuristic with no mathematical basis",
                        f"Legacy implementation deprecated in modern {subj}",
                    ],
                    "answer": f"Core conceptual definition and properties of {name}",
                    "explanation": f"In {subj}, {name} establishes the fundamental rules and formal properties required for problem solving.",
                    "objective": f"Recall foundational concepts and defining properties of {name}.",
                },
                {
                    "type": "true_false",
                    "text": f"True or False: The principles governing {name} apply consistently regardless of scale in {subj}.",
                    "options": ["True", "False"],
                    "answer": "True",
                    "explanation": f"Foundational principles of {name} remain invariant across scalable problem instances.",
                    "objective": f"Understand invariant properties of {name}.",
                },
                {
                    "type": "short_answer",
                    "text": f"Briefly explain the primary purpose of applying {name} in {subj}.",
                    "answer": f"To optimize structure, verify invariants, or compute deterministic outcomes in {name}.",
                    "explanation": f"{name} is applied to maintain structured guarantees and predictable results in {subj}.",
                    "objective": f"Explain practical utility of {name}.",
                },
            ]
        elif bloom in ["Apply", "Analyze"]:
            return [
                {
                    "type": "mcq",
                    "text": f"When implementing {name} under constrained conditions, which factor is most critical?",
                    "options": [
                        f"Boundary conditions and input invariant validation for {name}",
                        f"Ignoring base cases and edge cases",
                        f"Randomized state transitions without verification",
                        f"Suppressing error codes during computation",
                    ],
                    "answer": f"Boundary conditions and input invariant validation for {name}",
                    "explanation": f"Applying {name} correctly requires strict verification of boundary states to prevent runtime failures.",
                    "objective": f"Apply {name} to constrained problem domains.",
                },
                {
                    "type": "conceptual_application",
                    "text": f"Analyze how failure to handle boundary states affects overall system behavior in {name}.",
                    "answer": f"Leading to invalid state transitions, incorrect output, or catastrophic error propagation in {name}.",
                    "explanation": f"Boundary analysis in {name} is essential to ensure robustness under adverse input distributions.",
                    "objective": f"Analyze boundary failure modes in {name}.",
                },
                {
                    "type": "true_false",
                    "text": f"True or False: Decomposing a complex scenario in {name} into sub-components preserves linear solvability.",
                    "options": ["True", "False"],
                    "answer": "True",
                    "explanation": f"Modular decomposition allows independent analysis of sub-properties in {name}.",
                    "objective": f"Deconstruct multi-part problem instances in {name}.",
                },
            ]
        else:  # Evaluate / Create
            return [
                {
                    "type": "conceptual_application",
                    "text": f"Evaluate the trade-offs between computational overhead and precision when scaling {name}.",
                    "answer": f"Higher precision in {name} typically entails increased computational cost or latency trade-offs.",
                    "explanation": f"Advanced evaluation of {name} requires balancing resource utilization against accuracy requirements.",
                    "objective": f"Critically evaluate performance trade-offs in {name}.",
                },
                {
                    "type": "mcq",
                    "text": f"Which strategy best synthesizes modern best-practices with classical {name} architectures?",
                    "options": [
                        f"Hybrid integration combining verified {name} invariants with adaptive heuristics",
                        f"Complete abandonment of formal theoretical guarantees",
                        f"Brute-force iteration over infinite state spaces",
                        f"Hardcoding static lookup tables without dynamic adaptation",
                    ],
                    "answer": f"Hybrid integration combining verified {name} invariants with adaptive heuristics",
                    "explanation": f"Synthesizing optimal solutions in {name} merges deterministic guarantees with scalable heuristics.",
                    "objective": f"Synthesize novel architectures leveraging {name}.",
                },
                {
                    "type": "short_answer",
                    "text": f"Propose a verification criterion to benchmark the empirical correctness of an implementation of {name}.",
                    "answer": f"Unit test coverage across boundary conditions, formal assertion checking, and regression benchmarks.",
                    "explanation": f"Rigorous verification ensures implementation correctness matches mathematical models in {name}.",
                    "objective": f"Design validation benchmarks for {name}.",
                },
            ]


problem_generator = ProblemGenerator()
