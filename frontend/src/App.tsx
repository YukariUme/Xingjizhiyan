/** 路由表：按工作模式（教学 / 学习 / 研究）组织，保留旧路径重定向。 */

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { roleHome } from "./modes";
const Landing = lazy(() => import("./pages/Landing"));
const SearchPage = lazy(() => import("./pages/Search"));
const Workflows = lazy(() => import("./pages/Workflows"));
const TeacherDashboard = lazy(() => import("./pages/teacher/Dashboard"));
const TeacherCourses = lazy(() => import("./pages/teacher/Courses"));
const TeacherLessonPlan = lazy(() => import("./pages/teacher/LessonPlan"));
const TeacherAssignments = lazy(() => import("./pages/teacher/Assignments"));
const TeacherAssignmentDetail = lazy(() => import("./pages/teacher/AssignmentDetail"));
const TeacherGrading = lazy(() => import("./pages/teacher/Grading"));
const TeacherAnalytics = lazy(() => import("./pages/teacher/Analytics"));
const TeacherKnowledge = lazy(() => import("./pages/teacher/KnowledgeBase"));
const TeacherQuestionBank = lazy(() => import("./pages/teacher/QuestionBank"));
const StudentHome = lazy(() => import("./pages/student/Home"));
const StudentCourses = lazy(() => import("./pages/student/Courses"));
const StudentAssignments = lazy(() => import("./pages/student/Assignments"));
const StudentAssignmentDetail = lazy(() => import("./pages/student/AssignmentDetail"));
const StudentLearning = lazy(() => import("./pages/student/LearningCenter"));
const StudentTutor = lazy(() => import("./pages/student/Tutor"));
const CourseSpace = lazy(() => import("./pages/learn/CourseSpace"));
const ResearchWorkbench = lazy(() => import("./pages/research/Workbench"));
const ResearchPapers = lazy(() => import("./pages/research/Papers"));
const ResearchExplore = lazy(() => import("./pages/research/Explore"));
const ResearchCompare = lazy(() => import("./pages/research/Compare"));

function PageFallback() {
  return <div className="center"><span className="spinner" /> 页面加载中…</div>;
}

function RoleHome() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  return <Navigate to={roleHome(user.role)} replace />;
}

function OldRedirect({ prefix }: { prefix: string }) {
  const location = useLocation();
  const rest = location.pathname.replace(/^\/(teacher|student)/, "");
  return <Navigate to={`${prefix}${rest || ""}`} replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/search" element={<SearchPage />} />
          <Route element={<Layout />}>
            <Route path="/workflows" element={<Workflows />} />
          {/* 学习模式 */}
          <Route path="/learn" element={<StudentHome />} />
          <Route path="/learn/courses" element={<StudentCourses />} />
          <Route path="/learn/courses/:courseId" element={<CourseSpace />} />
          <Route path="/learn/assignments" element={<StudentAssignments />} />
          <Route path="/learn/assignments/:id" element={<StudentAssignmentDetail />} />
          <Route path="/learn/center" element={<StudentLearning />} />
          <Route path="/learn/tutor" element={<StudentTutor />} />
          {/* 教学模式 */}
          <Route path="/teach" element={<TeacherDashboard />} />
          <Route path="/teach/courses" element={<TeacherCourses />} />
          <Route path="/teach/design" element={<TeacherLessonPlan />} />
          <Route path="/teach/assignments" element={<TeacherAssignments />} />
          <Route path="/teach/assignments/:id" element={<TeacherAssignmentDetail />} />
          <Route path="/teach/grading/:submissionId" element={<TeacherGrading />} />
          <Route path="/teach/diagnostics" element={<TeacherAnalytics />} />
          <Route path="/teach/knowledge" element={<TeacherKnowledge />} />
          <Route path="/teach/question-bank" element={<TeacherQuestionBank />} />
          {/* 研究模式 */}
          <Route path="/research" element={<ResearchWorkbench />} />
          <Route path="/research/papers" element={<ResearchPapers />} />
          <Route path="/research/frontier" element={<ResearchExplore />} />
          <Route path="/research/compare" element={<ResearchCompare />} />
          </Route>
          <Route path="/role" element={<RoleHome />} />
          <Route path="/teacher/*" element={<OldRedirect prefix="/teach" />} />
          <Route path="/student/*" element={<OldRedirect prefix="/learn" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
