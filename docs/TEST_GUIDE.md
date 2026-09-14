# 测试指引

## 1. 后端基础检查

在项目根目录运行：

```powershell
python -m py_compile backend\app\api\submissions.py backend\app\api\analytics.py backend\app\services\grading_service.py backend\app\services\analytics_service.py backend\app\services\learning_state_service.py backend\app\services\learning_path_service.py backend\app\services\planner_service.py backend\app\services\agent\learning.py
```

预期：无报错。

## 2. 前端基础检查

在前端目录运行：

```powershell
npm run build
```

预期：打包成功，无语法错误。

## 3. 功能测试清单

### 提交作业
- 打开任意作业。
- 提交编程题或主观题。
- 检查提交后是否能正常返回结果。
- 检查学习中心是否自动刷新任务和计划。

### 教师批改
- 进入教师批改页。
- 完成主观题 AI 建议批改和教师确认。
- 检查学生画像、学习任务、学习路径是否刷新。

### 教学诊断
- 进入教师学情分析页。
- 生成教学诊断后，对任一建议执行“采纳 / 修改 / 拒绝”。
- 刷新页面，确认最近决策记录仍然可见。

### AI 导师
- 打开 AI 学科导师页面。
- 观察默认模式是否会根据画像和历史对话自动变化。
- 连续提问同一知识点，检查系统提示是否更偏向提示模式。

### 课程空间
- 进入课程首页。
- 检查是否出现“下一步建议”。
- 点击建议按钮，确认可跳转到对应页签。

### 学习中心
- 打开学习中心。
- 检查是否能看到统一学习状态和学习前后对比。
- 完成一次作业或测验后，刷新页面确认状态和推荐有变化。

## 4. 演示检查

- 登录学生账号。
- 先做一次提问，再提交一次作业或测验。
- 返回课程首页和导师页，确认“任务、建议、模式”有变化。
- 用浏览器无痕窗口再看一遍，确认首屏可直接演示。

## 5. 常见问题

- 如果 `py_compile` 报错，优先检查是否还有残留的字符串替换痕迹。
- 如果前端 build 报错，优先检查 `Tutor.tsx` 和 `CourseSpace.tsx` 的 JSX 是否闭合。
- 如果页面没刷新，确认后端接口是否已重启。
