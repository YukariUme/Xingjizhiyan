/** 与后端 API 对应的类型定义。 */

export type Role = "teacher" | "student" | "researcher";

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  identity?: string;
  modes?: string[];
  title: string;
  bio: string;
}

export interface LoginResult {
  token: string;
  user: User;
}

export interface Course {
  id: number;
  name: string;
  code: string;
  description: string;
  semester: string;
  teacher_id: number;
  created_at: string;
  student_count: number;
  assignment_count: number;
  pending_count: number;
}

export interface CourseInvitation {
  id: number;
  course_id: number;
  course_name: string;
  course_code: string;
  semester: string;
  teacher_name: string;
  student_id: number;
  student_name: string;
  student_username: string;
  status: "pending" | "accepted" | "declined" | "cancelled";
  created_at: string;
}

export interface KnowledgeJob {
  id: number;
  kind: "upload" | "import";
  status: "pending" | "running" | "success" | "failed";
  filename: string;
  course: string;
  progress: number;
  message: string;
  result: {
    document_id?: number;
    title?: string;
    results?: Array<{ filename: string; status: string; reason?: string; document_id?: number }>;
  };
  error: string;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: number;
  assignment_id: number;
  qtype: "programming" | "subjective" | "report";
  title: string;
  description: string;
  language: string;
  code_template: string;
  test_cases: TestCase[];
  max_score: number;
  knowledge_point_ids: number[];
}

export interface QuizQuestion {
  question_id: number;
  qtype: string;
  title: string;
  options: string[];
  max_score: number;
}

export interface TestCase {
  id: number;
  test_id?: number;
  name: string;
  check?: string;
  value?: string;
  hint?: string;
  input?: string;
  expected?: string;
  passed?: boolean;
  message?: string;
  actual?: string;
  time_ms?: number;
}

export interface Assignment {
  id: number;
  title: string;
  description: string;
  course_id: number;
  teacher_id: number;
  due_at: string;
  status: string;
  created_at: string;
  questions: Question[];
  course_name: string;
  submitted_count: number;
  student_count: number;
}

export interface CodeResult {
  source_code?: string;
  language?: string;
  verdict: string;
  passed_tests: number;
  total_tests: number;
  runtime_ms: number;
  error_message: string;
  judge_report: TestCase[];
}

export interface SubjectiveResult {
  content: string;
  ai_suggestion_score: number | null;
  ai_reasoning: string;
  ai_knowledge_points: string[];
  ai_error_analysis: string;
  ai_improvement: string;
  teacher_score: number | null;
  teacher_comment: string;
}

export interface SubmissionDetail {
  submission_id: number;
  assignment_id: number;
  assignment_title: string;
  question_id: number;
  question_title: string;
  question_description: string;
  max_score: number;
  test_cases: TestCase[];
  qtype: string;
  status: string;
  student_id: number;
  student_name: string;
  created_at: string;
  code: CodeResult | null;
  subjective: SubjectiveResult | null;
  score: number | null;
}

export interface MySubmission {
  submission_id: number;
  assignment_id: number;
  question_id: number;
  question_title: string;
  qtype: string;
  status: string;
  score: number | null;
  verdict: string | null;
  passed_tests: number | null;
  total_tests: number | null;
  error_message: string;
  ai_reviewed: boolean;
  teacher_reviewed: boolean;
  created_at: string;
  updated_at: string;
}

export interface GradingItem {
  submission_id: number;
  assignment_id: number;
  assignment_title: string;
  question_title: string;
  qtype: string;
  student_id: number;
  student_name: string;
  status: string;
  submitted_at: string;
  ai_suggestion_score: number | null;
  teacher_score: number | null;
  ai_reviewed: boolean;
}

export interface KnowledgeDoc {
  id: number;
  title: string;
  source: string;
  course: string;
  topic: string;
  chapter: string;
  difficulty: string;
  type: string;
  year: number;
  content: string;
  course_id: number | null;
  source_level: string;
  visibility: string;
  owner_id: number | null;
  page: string;
  document_type: string;
  size_chars: number;
  chunk_count: number;
  created_at: string | null;
}

export interface KnowledgeChunk {
  id: number;
  chunk_index: number;
  text: string;
  metadata: Record<string, unknown>;
}

export interface KnowledgePoint {
  id: number;
  name: string;
  subject: string;
  chapter: string;
  difficulty: string;
  description: string;
  prerequisites: string[];
}

export interface SearchResult {
  chunk: {
    id: number;
    text: string;
    metadata_json: Record<string, unknown>;
  };
  document: {
    id: number;
    title: string;
    source: string;
    course: string;
    topic: string;
    chapter: string;
    difficulty: string;
    type: string;
    year: number;
    content: string;
  };
  score: number;
}

export interface TutorReply {
  answer: string;
  mode: string;
  knowledge_points: string[];
  references: string[];
  conversation_id: number;
  grounded?: boolean;
  confidence?: number;
}

export interface DiagnosisResult {
  error_reason: string;
  knowledge_points: string[];
  thinking: string[];
  advice: string[];
  suggestion: string;
  line_anchors?: Array<{ line: number; note: string }>;
  mode: string;
}

export interface ChatHistoryItem {
  id: number;
  role: string;
  content: string;
  knowledge_points: string[];
  references: string[];
  created_at: string;
  grounded?: boolean;
}

export interface MasteryItem {
  knowledge_point_id: number;
  knowledge_point: string;
  subject: string;
  mastery: number;
  attempts: number;
  errors: number;
  level: string;
}

export interface StudentProfile {
  student_id: number;
  knowledge: MasteryItem[];
  weak_points: string[];
  strong_points: string[];
  avg_mastery: number;
  learning_states?: LearningStateItem[];
  progress_comparisons?: LearningComparison[];
}

export interface LearningStateItem {
  id: number;
  student_id: number;
  course_id: number;
  knowledge_point_id: number;
  knowledge_point: string;
  subject: string;
  mastery_score: number;
  confidence: number;
  error_count: number;
  recent_error_count: number;
  consecutive_error_count: number;
  success_count: number;
  last_learning_at: string | null;
  last_assessment_at: string | null;
  recent_question_count: number;
  learning_stability: number;
  state: "STRUGGLING" | "REVIEW" | "STABLE" | "STRONG" | string;
  state_reason: string;
  updated_at: string | null;
}

export interface LearningComparison {
  id: number;
  student_id: number;
  course_id: number | null;
  knowledge_point_id: number | null;
  knowledge_point: string;
  before_mastery: number;
  after_mastery: number;
  before_state: string;
  after_state: string;
  interventions: string[];
  evidence: Record<string, unknown>;
  is_demo: boolean;
  created_at: string;
}

export interface TeacherSuggestionDecision {
  id: string;
  suggestion_id: string;
  course_id: number | null;
  teacher_id: number;
  action: "ACCEPT" | "EDIT" | "REJECT" | string;
  original_suggestion: string;
  modified_content: string;
  created_at: string;
}

export interface Recommendation {
  id: number;
  knowledge_point_id: number | null;
  knowledge_point: string;
  reason: string;
  resource_title: string;
  resource_type: "chapter" | "exercise" | "experiment" | "paper" | "next";
  resource_ref: Record<string, unknown>;
  priority: number;
  created_at: string;
}

export interface Paper {
  id: number;
  title: string;
  authors: string[];
  abstract: string;
  venue: string;
  year: number;
  topics: string[];
  keywords: string[];
  citations: number;
  url: string;
  is_hot: boolean;
  status: string;
  progress: number;
  content?: string;
}

export interface PaperAnalysis {
  paper_id: number;
  title: string;
  summary: string;
  research_question: string;
  method: string;
  experiments: string;
  conclusion: string;
  limitations: string;
  future: string;
  references: Array<{ title: string; source: string; course: string; chapter: string; snippet: string; source_level?: string }>;
  knowledge_points: string[];
  provider?: string;
}

export interface FrontierResult {
  topic: string;
  directions: string[];
  papers: Array<{ title: string; year: number }>;
  hot_topics: string[];
  methods: Array<{ name: string; count: number }>;
  trend: Array<{ year: number; count: number }>;
  references: Array<{ title: string; source: string; course: string; snippet: string }>;
}

export interface HotspotDirection {
  id: string;
  name: string;
  label: string;
  description: string;
  venues: string[];
}

export interface HotspotPaper {
  title: string;
  url: string;
  authors: string[];
  year: number;
  venue: string;
  summary: string;
  source: "curated" | "arxiv";
  tag: string;
}

export interface HotspotData {
  direction: HotspotDirection;
  papers: HotspotPaper[];
  updated_at: string;
  source: "curated" | "arxiv";
  refresh_hours: number;
  note: string;
}

export interface Workbench {
  topics: Array<{ id: number; name: string; description: string }>;
  recent_papers: Paper[];
  recommended_papers: Paper[];
  favorite_papers: Paper[];
  reading_records: Array<{ paper_id: number; status: string; progress: number; last_read_at: string }>;
}

export interface ClassAnalytics {
  course_id: number;
  course_name: string;
  total_students: number;
  assignment_count: number;
  submission_count: number;
  graded_count: number;
  avg_accuracy: number;
  knowledge_accuracy: Array<{
    knowledge_point_id: number;
    name: string;
    subject: string;
    attempts: number;
    correct: number;
    accuracy: number;
  }>;
  high_frequency_errors: Array<{
    knowledge_point_id: number;
    name: string;
    subject: string;
    accuracy: number;
    attempts: number;
  }>;
  ability_distribution: Array<{ band: string; count: number }>;
  weak_points: string[];
}

export interface LessonPlan {
  id: number;
  course: string;
  chapter: string;
  topic: string;
  grade: string;
  objectives: string;
  knowledge_points: string[];
  key_points: string[];
  difficulties: string[];
  flow: Array<{ step: string; content: string }>;
  cases: string[];
  exercises: Array<{ title: string; desc: string }>;
  homework: string[];
  created_at: string;
  provider?: string;
}

export interface Activity {
  id: number;
  user_id: number;
  role: string;
  kind: string;
  title: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowStepDef {
  id: string;
  label: string;
  type: string;
  tool: string;
}

export interface WorkflowDef {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStepDef[];
}

export interface WorkflowStepRun {
  id: number;
  step_id: string;
  label: string;
  status: "running" | "success" | "failed" | "awaiting_approval" | "skipped";
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error: string;
  started_at: string;
  finished_at: string | null;
}

export interface WorkflowRun {
  id: number;
  definition_id: string;
  name: string;
  status: "running" | "awaiting_approval" | "success" | "failed";
  owner_id: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error: string;
  created_at: string;
  finished_at: string | null;
  steps: WorkflowStepRun[];
}

export type SessionStepType =
  | "goal"
  | "warmup"
  | "explain"
  | "visualize"
  | "code"
  | "practice"
  | "check"
  | "wrapup";

export interface SessionStep {
  type: SessionStepType;
  text?: string;
  question?: string;
  options?: string[];
  title?: string;
  content?: string;
  example?: string;
  anchor?: string;
  kind?: string;
  payload?: Record<string, unknown>;
  language?: string;
  code?: string;
  expected_output?: string;
  qtype?: string;
  answer?: unknown;
  hint?: string;
  prompt?: string;
  summary?: string;
  weak_points?: string[];
  suggestion?: string;
}

export interface SessionReference {
  title: string;
  source: string;
  course?: string;
  chapter?: string;
  source_level?: string;
  page?: string;
  snippet?: string;
  score?: number;
}

export interface LearningSession {
  id: number;
  title: string;
  depth: string;
  mode: string;
  course_id: number;
  chapter_id: number | null;
  knowledge_point_id: number | null;
  current_index: number;
  status: string;
  steps: SessionStep[];
  provider?: string;
  ai_generated?: boolean;
  references?: SessionReference[];
  created_at: string;
}
