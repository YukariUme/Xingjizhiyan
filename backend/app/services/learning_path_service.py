"""个性化学习路径服务：基于规则 + 知识画像生成推荐。"""

from sqlalchemy.orm import Session

from app.mock.questions import EXERCISE_BANK
from app.models import LearningRecommendation
from app.repositories.learning_repo import LearningRepository


class LearningPathService:
    @staticmethod
    def generate(db: Session, student_id: int) -> list[LearningRecommendation]:
        """根据薄弱知识点生成：复习章节 / 推荐练习 / 推荐实验 / 论文 / 下一阶段。"""
        profiles = LearningRepository.list_profiles(db, student_id)
        weak = [p for p in profiles if (p.mastery or 0) < 60]
        recommendations: list[LearningRecommendation] = []
        if not weak:
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
            LearningRepository.replace_recommendations(db, recommendations)
            return recommendations

        from app.models import KnowledgeDocument, KnowledgePoint
        from app.repositories.knowledge_repo import KnowledgeRepository

        for p in weak[:5]:
            kp = db.get(KnowledgePoint, p.knowledge_point_id)
            if not kp:
                continue
            doc = None
            for d in KnowledgeRepository.list_documents(db, kp.subject):
                if kp.name in (d.topic or "") or kp.name in (d.title or ""):
                    doc = d
                    break
            if not doc and KnowledgeRepository.list_documents(db, kp.subject):
                doc = KnowledgeRepository.list_documents(db, kp.subject)[0]
            # 复习章节
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=kp.id,
                    reason=f"「{kp.name}」掌握度 {p.mastery:.0f}%，低于 60%",
                    resource_title=doc.title if doc else f"{kp.chapter} 讲义",
                    resource_type="chapter",
                    resource_ref={
                        "document_id": doc.id if doc else None,
                        "course": kp.subject,
                        "chapter": kp.chapter,
                    },
                    priority=5,
                )
            )
            # 推荐练习
            exercises = EXERCISE_BANK.get(kp.name, [])
            if exercises:
                recommendations.append(
                    LearningRecommendation(
                        student_id=student_id,
                        knowledge_point_id=kp.id,
                        reason=f"针对「{kp.name}」强化训练",
                        resource_title=exercises[0],
                        resource_type="exercise",
                        resource_ref={"all": exercises, "course": kp.subject},
                        priority=5,
                    )
                )
            # 推荐实验
            recommendations.append(
                LearningRecommendation(
                    student_id=student_id,
                    knowledge_point_id=kp.id,
                    reason="通过动手实验巩固理解",
                    resource_title=f"{kp.name}专项实验",
                    resource_type="experiment",
                    resource_ref={"course": kp.subject, "chapter": kp.chapter},
                    priority=4,
                )
            )
        # 下一阶段：相关论文
        from app.repositories.research_repo import ResearchRepository

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
                    priority=2,
                )
            )
        LearningRepository.replace_recommendations(db, recommendations)
        return recommendations

