"""个性化学习路径服务：基于规则 + 知识画像生成推荐。"""

from sqlalchemy.orm import Session

from app.mock.questions import EXERCISE_BANK
from app.models import Course, KnowledgePoint, LearningRecommendation
from app.repositories.learning_repo import LearningRepository
from app.services.analytics_service import AnalyticsService
from app.services.learning_state_service import LearningStateEngine


class LearningPathService:
    @staticmethod
    def generate(db: Session, student_id: int) -> list[LearningRecommendation]:
        """根据薄弱知识点与最近行为生成：复习章节 / 推荐练习 / 推荐实验 / 论文 / 下一步。"""
        profiles = LearningRepository.list_profiles(db, student_id)
        states = {s.knowledge_point_id: s for s in LearningStateEngine.list_states(db, student_id)}
        weak = [p for p in profiles if (p.mastery or 0) < 60]
        behavior = AnalyticsService.recent_behavior_window(db, student_id, profiles)
        topic_counts = behavior["topic_counts"]
        wrong_points = behavior["recent_wrong_points"]
        wrong_submissions = behavior["recent_wrong_submissions"]
        short_sessions = behavior["short_sessions"]
        recommendations: list[LearningRecommendation] = []

        from app.repositories.knowledge_repo import KnowledgeRepository
        from app.repositories.research_repo import ResearchRepository

        # 1) 最近连续错题 / 反复出错点
        if wrong_submissions:
            top_wrong = wrong_points[0] if wrong_points else None
            if top_wrong:
                kp = db.get(KnowledgePoint, top_wrong["knowledge_point_id"])
                course = db.query(Course).filter(Course.name == kp.subject).first() if kp else None
                state = states.get(top_wrong["knowledge_point_id"])
                recommendations.append(
                    LearningRecommendation(
                        student_id=student_id,
                        knowledge_point_id=top_wrong["knowledge_point_id"],
                        reason=(
                            f"最近在相关题目上连续错了 {behavior['wrong_streak']} 次，"
                            f"先回看「{top_wrong['name']}」的错因，再做同类重做。"
                            + (f" 当前状态 {state.state}。" if state else "")
                        ),
                        resource_title=f"回看「{top_wrong['name']}」",
                        resource_type="next",
                        resource_ref={
                            "action": "review_again",
                            "knowledge_point_id": top_wrong["knowledge_point_id"],
                            "course_id": course.id if course else None,
                            "subject": kp.subject if kp else "",
                            "state": state.state if state else "STRUGGLING",
                        },
                        priority=9,
                    )
                )

        # 2) 当前薄弱知识点 → 章节 / 练习 / 实验
        for p in sorted(weak, key=lambda x: x.mastery)[:5]:
            kp = db.get(KnowledgePoint, p.knowledge_point_id)
            if not kp:
                continue
            course = db.query(Course).filter(Course.name == kp.subject).first()
            state = states.get(kp.id)
            topic_hits = topic_counts.get(kp.name, 0)
            docs = KnowledgeRepository.list_documents(db, kp.subject)
            doc = None
            for d in docs:
                if kp.name in (d.topic or "") or kp.name in (d.title or ""):
                    doc = d
                    break
            if not doc and docs:
                doc = docs[0]
            priority_boost = min(3, topic_hits) + (1 if short_sessions else 0)
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=kp.id,
                    reason=(
                        f"「{kp.name}」掌握度 {p.mastery:.0f}%，低于 60%"
                        + (f"；最近答疑里又提到 {topic_hits} 次" if topic_hits else "")
                        + (f"；当前状态 {state.state}" if state else "")
                    ),
                    resource_title=doc.title if doc else f"{kp.chapter} 讲义",
                    resource_type="chapter",
                    resource_ref={
                        "document_id": doc.id if doc else None,
                        "course_id": course.id if course else None,
                        "course": kp.subject,
                        "chapter": kp.chapter,
                        "knowledge_point_id": kp.id,
                        "state": state.state if state else "",
                    },
                    priority=6 + priority_boost,
                )
            )
            exercises = EXERCISE_BANK.get(kp.name, [])
            if exercises:
                recommendations.append(
                    LearningRecommendation(
                        student_id=student_id,
                        knowledge_point_id=kp.id,
                    reason=f"针对「{kp.name}」强化训练",
                        resource_title=exercises[0],
                        resource_type="exercise",
                        resource_ref={
                        "all": exercises,
                        "course_id": course.id if course else None,
                        "knowledge_point_id": kp.id,
                        "state": state.state if state else "",
                    },
                    priority=6 + priority_boost,
                )
            )
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=kp.id,
                    reason=(
                        "通过动手实验巩固理解"
                        + ("，适合把最近讲过的内容再跑一遍" if short_sessions else "")
                        + (f"；当前状态 {state.state}" if state else "")
                    ),
                    resource_title=f"{kp.name}专项实验",
                    resource_type="experiment",
                    resource_ref={
                        "course_id": course.id if course else None,
                        "chapter": kp.chapter,
                        "knowledge_point_id": kp.id,
                        "state": state.state if state else "",
                    },
                    priority=5 + min(2, priority_boost),
                )
            )

        # 3) 最近反复提问的主题，但还没有明显薄弱点
        if topic_counts:
            top_topic, top_count = topic_counts.most_common(1)[0]
            if top_count >= 2:
                related_state = next((s for s in states.values() if s.state in {"REVIEW", "STRUGGLING"}), None)
                recommendations.append(
                    LearningRecommendation(
                        student_id=student_id,
                        knowledge_point_id=None,
                        reason=f"你最近在答疑里多次提到「{top_topic}」，建议先回看再继续推进。",
                        resource_title=f"回看最近高频主题「{top_topic}」",
                        resource_type="next",
                        resource_ref={"topic": top_topic, "hits": top_count, "page": "learning", "action": "review_again", "state": related_state.state if related_state else "REVIEW"},
                        priority=8,
                    )
                )

        # 4) 论文与进阶阅读
        kp_names = " ".join(
            (db.get(KnowledgePoint, p.knowledge_point_id).name if db.get(KnowledgePoint, p.knowledge_point_id) else "")
            for p in weak[:3]
        )
        papers = ResearchRepository.search_papers(db, kp_names or "计算机", limit=3)
        for paper in papers[:2]:
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=None,
                    reason="掌握基础后进阶科研阅读",
                    resource_title=paper.title,
                    resource_type="paper",
                    resource_ref={"paper_id": paper.id, "page": "research"},
                    priority=3,
                )
            )

        if not recommendations:
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=None,
                    reason="当前没有明显薄弱知识点",
                    resource_title="进入科研探索，阅读本领域前沿论文",
                    resource_type="paper",
                    resource_ref={"page": "research"},
                    priority=3,
                )
            )

        recommendations.sort(key=lambda r: (-r.priority, r.created_at))
        LearningRepository.replace_recommendations(db, recommendations)
        return recommendations
