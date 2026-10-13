export interface Criterion {
  points: number;
  reasoning: string;
  evidence_status: string;
  quotes: string[];
}
export interface Evaluation {
  score: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
  better_answer: string;
  rubric_version?: string;
  rubric?: Record<string, Criterion>;
}
export interface SessionSummary {
  id: string;
  title: string;
  status: string;
  total_questions: number;
  answered_questions: number;
  average_score: number | null;
  created_at: string;
  updated_at: string;
}
export interface Answer {
  question_index: number;
  question: string;
  answer_text: string;
  evaluation: Evaluation;
  created_at: string;
}
export interface Session extends SessionSummary {
  questions: string[];
  role_context: string;
  current_question_index: number;
  current_question: string | null;
  followups_enabled: boolean;
  current_question_is_followup: boolean;
  followups: {
    question_index: number;
    parent_question_index: number;
    reason: string;
  }[];
  answers: Answer[];
}
export interface Progress {
  summary: {
    sessions: number;
    completed_sessions: number;
    answers: number;
    average_score: number | null;
    score_change: number | null;
    trend_window: number;
    practice_score_target: number;
  };
  score_trend: { date: string; average_score: number; answer_count: number }[];
  session_scores: {
    session_id: string;
    title: string;
    answer_count: number;
    average_score: number;
  }[];
  recurring_weaknesses: {
    theme: string;
    answer_count: number;
    session_count: number;
    examples: string[];
  }[];
  topics: {
    topic: string;
    answer_count: number;
    average_score: number;
    needs_practice: boolean;
    reasons: string[];
    suggestions: string[];
    practice_questions: { question: string; score: number }[];
  }[];
}
export interface HistoryItem {
  id: number;
  event_type: string;
  title: string;
  created_at: string;
  payload?: Record<string, unknown>;
}
export interface UIConfig {
  max_resume_upload_bytes: number;
  max_audio_upload_bytes: number;
  recording_silence_seconds: number;
  recording_max_seconds: number;
  recording_start_timeout_seconds: number;
  recording_energy_threshold: number;
  live_transcription_language: string;
  max_session_questions: number;
  max_session_answer_characters: number;
}
export type Result = Record<string, unknown>;
