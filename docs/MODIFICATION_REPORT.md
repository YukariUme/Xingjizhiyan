# 修改报告

## 本次完成

1. 新增统一学习状态引擎 `learning_state_service.py`，把画像、答题、答疑、学习节奏收敛成 `STRUGGLING / REVIEW / STABLE / STRONG`。
2. 在学生学习中心新增“统一学习状态”和“学习前后对比”展示，评委可以直接看到状态变化和证据链。
3. 个性化任务、学习计划和推荐路径改为读取行为窗口与学习状态，不再只依赖静态画像。
4. 教师教学诊断新增“采纳 / 修改 / 拒绝”留痕接口，并在教师端页面展示最近决策记录。
5. 在教师批改确认后继续保留学情回流，教师给分会刷新学生画像、任务和学习路径。
6. 在学生 AI 导师中引入最近行为窗口，把最近 7 天学习记录、连续错题、高频提问和学习节奏带入上下文。
7. 课程学习空间首页新增“下一步建议”，把用户引导到更合适的下一步页面。
8. AI 导师页面默认模式改为“基于画像 + 重复提问”的自适应判断。

## 代码影响点

- `backend/app/models/learning_state.py`
- `backend/app/services/learning_state_service.py`
- `backend/app/api/analytics.py`
- `backend/app/api/submissions.py`
- `backend/app/services/grading_service.py`
- `backend/app/services/analytics_service.py`
- `backend/app/services/planner_service.py`
- `backend/app/services/learning_path_service.py`
- `backend/app/services/agent/learning.py`
- `frontend/src/pages/student/LearningCenter.tsx`
- `frontend/src/pages/student/Tutor.tsx`
- `frontend/src/pages/learn/CourseSpace.tsx`
- `frontend/src/pages/teacher/Analytics.tsx`
- `frontend/src/types.ts`

## 这次改动的作用

- 让个性化推荐不再只看薄弱知识点，而是结合最近行为与统一学习状态。
- 让教师批改、教学诊断和学生学习路径之间形成闭环。
- 让课程页、学习中心和导师页更像“主动陪学”，减少用户手动找入口。

## 说明

本次改动属于轻量闭环增强，没有重构数据库结构，也没有新增外部依赖。
