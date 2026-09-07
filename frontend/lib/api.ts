export type AuthResponse = {
  access_token: string;
  token_type: string;
  email_status?: string;
  email_detail?: string;
};

export type UserProfile = {
  id: number;
  email: string;
  name: string;
  role: string;
  email_verified: boolean;
};

export type Reminder = {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  reminder_datetime: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AssistantResponse = {
  reply: string;
  source: string;
};

export type Project = {
  id: number;
  title: string;
  domain: string;
  description?: string | null;
  status: string;
  user_id?: number;
  document_count?: number;
  analysis_count?: number;
};

export type Reference = {
  id: number;
  project_id: number;
  owner_id: number;
  title: string;
  url: string | null;
  authors: string | null;
  year: number | null;
  notes: string | null;
  reference_type: string;
  created_at: string;
};

export type ResearchPaper = {
  id: number;
  project_id: number;
  owner_id: number;
  title: string;
  content: string;
  word_count: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Paper = {
  id: number;
  title: string;
  abstract: string | null;
  authors: string | null;
  venue: string | null;
  year: number | null;
  doi: string | null;
  citation_count: number;
  quality_score: number;
  evidence_level: string;
  is_recent?: boolean;
};

export type ResearchDocument = {
  id: number;
  paper_id: number | null;
  project_id?: number | null;
  filename: string;
  content_type: string;
  extracted_characters: number;
  created_at: string;
};

export type Notification = {
  id: number;
  type: string;
  message: string;
  read_at: string | null;
  created_at: string;
};

export type FollowUp = {
  id: number;
  project_id: number | null;
  title: string;
  message: string;
  due_at: string | null;
  priority: string;
  status: string;
  snoozed_until: string | null;
  completed_at: string | null;
  created_at: string;
};

export type LawProject = {
  id: number;
  title: string;
  legal_question: string;
  jurisdiction: string | null;
  disclaimer: string;
  created_at: string;
};

export type LawSource = {
  id: number;
  project_id: number;
  label: string;
  source_url: string;
  source_type: 'fact' | 'source' | 'inference' | 'suggestion';
  excerpt: string | null;
  created_at: string;
};

export type ResearchAnalysis = {
  plan: {
    idea: string;
    objectives: string[];
    status: string;
  };

  literature: {
    query: string;
    results: Array<{
      title: string;
      authors: string[];
      abstract: string;
      year: number;
      url: string;
      source: string;
      relevance_score?: number;
    }>;
    status: string;
    source?: string;
  };

  analysis: {
    papers_processed: number;

    papers: Array<{
      title: string;
      authors: string[];
      year: number;
      url: string;
      methods: string[];
      abstract_summary: string;
      limitations: string[];
    }>;

    method_distribution: Record<string, number>;

    summary: string;

    key_findings: string[];
  };

  research_gaps: {
    research_idea: string;

    gaps: Array<{
      title: string;
      description: string;
      importance: string;
    }>;

    papers_compared: number;

    methods_observed: Record<string, number>;

    status: string;
  };

  datasets: {
    research_idea: string;

    recommendations: Array<{
      name: string;
      purpose: string;
      source: string;
      use: string;
      url?: string;
    }>;

    status: string;
  };

  experiments: {
    research_idea: string;

    baseline: string;

    proposed_system: string;

    experiments: Array<{
      name: string;
      objective: string;
      metrics: string[];
    }>;

    datasets_available: number;

    papers_available: number;

    gaps_identified: number;

    status: string;
  };

  roadmap: {
    idea: string;

    milestones: Array<{
      step: number;
      title: string;
      description: string;
    }>;

    analysis_summary: string;

    status: string;
  };

  evidence_backed: boolean;

  ai_generated_opportunities: string[];

  _documents_used?: Array<{ id: number; filename: string }>;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

const CONNECTION_ERROR =
  'ResearchOS could not connect to the research server. Confirm that the backend is running at http://localhost:8000, then try again.';

const MAX_RETRIES = 2;
const BASE_RETRY_DELAY = 1000;

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  retries = MAX_RETRIES,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (retries > 0 && error instanceof TypeError) {
      await sleep(BASE_RETRY_DELAY);
      return request<T>(path, options, token, retries - 1);
    }
    const detail = error instanceof Error && error.message
      ? ` Technical detail: ${error.message}`
      : '';
    throw new Error(`${CONNECTION_ERROR}${detail}`);
  }

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => null);

    throw new Error(
      error?.detail ??
        'The request could not be completed.'
    );
  }

  // 204 No Content — DELETE endpoints return empty body
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function register(
  email: string,
  password: string,
  name: string
) {
  return request<AuthResponse>(
    '/api/v1/auth/register',
    {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        name,
      }),
    }
  );
}

export function login(
  email: string,
  password: string
) {
  return request<AuthResponse>(
    '/api/v1/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
      }),
    }
  );
}

export function getMe(token: string) {
  return request<UserProfile>(
    '/api/v1/auth/me',
    {},
    token
  );
}

// ---------------------------------------------------------
// EMAIL VERIFICATION & PASSWORD RESET
// ---------------------------------------------------------

export function verifyEmail(email: string, otp: string, token?: string) {
  return request<{ message: string }>(
    '/api/v1/auth/verify-email',
    {
      method: 'POST',
      body: JSON.stringify({ email, otp }),
      ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
    }
  );
}

export function resendOtp(email: string, token?: string) {
  return request<{ message: string; expires_in_seconds: number }>(
    '/api/v1/auth/resend-otp',
    {
      method: 'POST',
      body: JSON.stringify({ email }),
      ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
    }
  );
}

export function forgotPassword(email: string) {
  return request<{ message: string }>(
    '/api/v1/auth/forgot-password',
    {
      method: 'POST',
      body: JSON.stringify({ email }),
    }
  );
}

export function verifyResetOtp(email: string, otp: string) {
  return request<{ message: string }>(
    '/api/v1/auth/verify-reset-otp',
    {
      method: 'POST',
      body: JSON.stringify({ email, otp }),
    }
  );
}

export function resetPassword(email: string, otp: string, newPassword: string) {
  return request<{ message: string }>(
    '/api/v1/auth/reset-password',
    {
      method: 'POST',
      body: JSON.stringify({ email, otp, new_password: newPassword }),
    }
  );
}

// ---------------------------------------------------------
// REMINDERS
// ---------------------------------------------------------

export function listReminders(token: string) {
  return request<Reminder[]>('/api/v1/reminders/', {}, token);
}

export function createReminder(
  token: string,
  title: string,
  description: string | null,
  reminderDatetime: string
) {
  return request<Reminder>(
    '/api/v1/reminders/',
    {
      method: 'POST',
      body: JSON.stringify({
        title,
        description,
        reminder_datetime: reminderDatetime,
      }),
    },
    token
  );
}

export function updateReminder(
  token: string,
  reminderId: number,
  data: { title?: string; description?: string | null; reminder_datetime?: string }
) {
  return request<Reminder>(
    `/api/v1/reminders/${reminderId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
    token
  );
}

export function completeReminder(token: string, reminderId: number) {
  return request<Reminder>(
    `/api/v1/reminders/${reminderId}/complete`,
    { method: 'POST' },
    token
  );
}

export function deleteReminder(token: string, reminderId: number) {
  return request<void>(
    `/api/v1/reminders/${reminderId}`,
    { method: 'DELETE' },
    token
  );
}

// ---------------------------------------------------------
// ASSISTANT
// ---------------------------------------------------------

export function sendAssistantMessage(
  token: string,
  message: string,
  projectId?: number,
  history?: Array<{ role: string; content: string }>,
) {
  return request<AssistantResponse>(
    '/api/v1/assistant/chat',
    {
      method: 'POST',
      body: JSON.stringify({
        message,
        project_id: projectId ?? null,
        history: history ?? null,
      }),
    },
    token
  );
}

export function listProjects(
  token: string
) {
  return request<Project[]>(
    '/api/v1/projects/',
    {},
    token
  );
}

export function deleteProject(token: string, projectId: number) {
  return request<void>(
    `/api/v1/projects/${projectId}`,
    { method: 'DELETE' },
    token
  );
}

export function getDocumentContent(token: string, docId: number) {
  return request<{ id: number; filename: string; extracted_text: string; extracted_characters: number; project_id: number | null }>(
    `/api/v1/papers/documents/${docId}/content`,
    {},
    token
  );
}

export function getDocumentSummary(token: string, docId: number) {
  return request<{ id: number; filename: string; sections_detected: string[]; keywords_found: string[]; preview: string }>(
    `/api/v1/papers/documents/${docId}/summary`,
    {},
    token
  );
}

// ---------------------------------------------------------
// RESEARCH PAPERS (per-project editor)
// ---------------------------------------------------------

export function getProjectResearchPaper(token: string, projectId: number) {
  return request<ResearchPaper | null>(
    `/api/v1/research-papers/project/${projectId}`,
    {},
    token
  );
}

export function saveProjectResearchPaper(
  token: string,
  projectId: number,
  title: string,
  content: string
) {
  return request<ResearchPaper>(
    `/api/v1/research-papers/project/${projectId}`,
    {
      method: 'POST',
      body: JSON.stringify({ title, content }),
    },
    token
  );
}

export function updateResearchPaper(
  token: string,
  paperId: number,
  data: { title?: string; content?: string }
) {
  return request<ResearchPaper>(
    `/api/v1/research-papers/${paperId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
    token
  );
}

// ---------------------------------------------------------
// PROJECT-SCOPED DOCUMENTS
// ---------------------------------------------------------

export function listProjectDocuments(token: string, projectId: number) {
  return request<ResearchDocument[]>(
    `/api/v1/papers/documents/project/${projectId}`,
    {},
    token
  );
}

export function createProject(
  token: string,
  title: string,
  domain: string
) {
  return request<Project & { user_id: number }>(
    '/api/v1/projects/',
    {
      method: 'POST',
      body: JSON.stringify({
        title,
        domain,
      }),
    },
    token
  );
}

export function listPapers(
  token: string
) {
  return request<Paper[]>(
    '/api/v1/papers/',
    {},
    token
  );
}

export function searchPapers(
  token: string,
  query: string
) {
  return request<Paper[]>(
    `/api/v1/papers/search?q=${encodeURIComponent(query)}`,
    {},
    token
  );
}

export function createPaper(
  token: string,
  title: string,
  abstract: string
) {
  return request<Paper>(
    '/api/v1/papers/',
    {
      method: 'POST',
      body: JSON.stringify({
        title,
        abstract,
      }),
    },
    token
  );
}

export function updatePaper(
  token: string,
  paperId: number,
  data: { title?: string; abstract?: string }
) {
  return request<Paper>(
    `/api/v1/papers/${paperId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
    token
  );
}

export function deletePaper(
  token: string,
  paperId: number
) {
  return request<void>(
    `/api/v1/papers/${paperId}`,
    {
      method: 'DELETE',
    },
    token
  );
}

export async function uploadResearchDocument(
  token: string,
  file: File,
  paperId?: number,
  projectId?: number
) {
  const body = new FormData();
  body.append('file', file);
  const params = new URLSearchParams();
  if (paperId) params.set('paper_id', String(paperId));
  if (projectId) params.set('project_id', String(projectId));
  const qs = params.toString() ? `?${params.toString()}` : '';
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/papers/upload${qs}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      await sleep(BASE_RETRY_DELAY);
      try {
        response = await fetch(`${API_BASE_URL}/api/v1/papers/upload${qs}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body,
        });
      } catch (retryError) {
        const detail = retryError instanceof Error && retryError.message
          ? ` Technical detail: ${retryError.message}`
          : '';
        throw new Error(`${CONNECTION_ERROR}${detail}`);
      }
    } else {
      const detail = error instanceof Error && error.message
        ? ` Technical detail: ${error.message}`
        : '';
      throw new Error(`${CONNECTION_ERROR}${detail}`);
    }
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? 'The document could not be uploaded.');
  }  return response.json() as Promise<ResearchDocument>;
}

export function listDocuments(token: string) {
  return request<ResearchDocument[]>(
    '/api/v1/papers/documents',
    {},
    token
  );
}

export function deleteDocument(token: string, docId: number) {
  return request<void>(
    `/api/v1/papers/documents/${docId}`,
    { method: 'DELETE' },
    token
  );
}


export function listNotifications(
  token: string
) {
  return request<Notification[]>(
    '/api/v1/notifications/',
    {},
    token
  );
}

export function markNotificationRead(
  token: string,
  notificationId: number
) {
  return request<Notification>(
    `/api/v1/notifications/${notificationId}/read`,
    {
      method: 'PATCH',
    },
    token
  );
}

export function listFollowUps(token: string) {
  return request<FollowUp[]>('/api/v1/followups/', {}, token);
}

export function createFollowUp(token: string, title: string, message: string, projectId?: number) {
  return request<FollowUp>('/api/v1/followups/', {
    method: 'POST',
    body: JSON.stringify({ title, message, project_id: projectId }),
  }, token);
}

export function completeFollowUp(token: string, followupId: number) {
  return request<FollowUp>(`/api/v1/followups/${followupId}/complete`, { method: 'POST' }, token);
}

export function snoozeFollowUp(token: string, followupId: number) {
  return request<FollowUp>(`/api/v1/followups/${followupId}/snooze?hours=24`, { method: 'POST' }, token);
}

export function listLawProjects(token: string) {
  return request<LawProject[]>('/api/v1/law/projects', {}, token);
}

export function createLawProject(token: string, title: string, legalQuestion: string, jurisdiction: string) {
  return request<LawProject>('/api/v1/law/projects', {
    method: 'POST',
    body: JSON.stringify({ title, legal_question: legalQuestion, jurisdiction: jurisdiction || null }),
  }, token);
}

export function listLawSources(token: string, projectId: number) {
  return request<LawSource[]>(`/api/v1/law/projects/${projectId}/sources`, {}, token);
}

export function addLawSource(token: string, projectId: number, label: string, sourceUrl: string, sourceType: LawSource['source_type'], excerpt: string) {
  return request<LawSource>(`/api/v1/law/projects/${projectId}/sources`, {
    method: 'POST',
    body: JSON.stringify({ label, source_url: sourceUrl, source_type: sourceType, excerpt: excerpt || null }),
  }, token);
}

export function analyzeResearch(
  token: string,
  idea: string
) {
  return request<ResearchAnalysis>(
    `/api/v1/research/analyze?idea=${encodeURIComponent(
      idea
    )}`,
    {
      method: 'POST',
    },
    token
  );
}

export function analyzeLocalResearch(
  token: string,
  idea: string,
  documentIds?: number[],
  projectId?: number
) {
  const params = new URLSearchParams({ idea });
  if (documentIds) {
    documentIds.forEach((id) => params.append('document_ids', String(id)));
  }
  if (projectId) {
    params.set('project_id', String(projectId));
  }
  return request<ResearchAnalysis>(
    `/api/v1/research/analyze-local?${params.toString()}`,
    { method: 'POST' },
    token
  );
}

export function saveAnalysis(
  token: string,
  projectId: number,
  researchIdea: string,
  documentIds: number[],
  resultJson: string
) {
  return request<{ id: number; project_id: number; created_at: string }>(
    '/api/v1/research/save-analysis',
    {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        research_idea: researchIdea,
        document_ids: documentIds,
        result_json: resultJson,
      }),
    },
    token
  );
}

// ---------------------------------------------------------
// REFERENCES
// ---------------------------------------------------------

export function listReferences(token: string, projectId: number) {
  return request<Reference[]>(
    `/api/v1/references/project/${projectId}`,
    {},
    token
  );
}

export function createReference(
  token: string,
  projectId: number,
  data: { title: string; url?: string; authors?: string; year?: number; notes?: string; reference_type?: string }
) {
  return request<Reference>(
    `/api/v1/references/project/${projectId}`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    token
  );
}

export function updateReference(
  token: string,
  refId: number,
  data: { title?: string; url?: string; authors?: string; year?: number; notes?: string }
) {
  return request<Reference>(
    `/api/v1/references/${refId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
    token
  );
}

export function deleteReference(token: string, refId: number) {
  return request<void>(
    `/api/v1/references/${refId}`,
    { method: 'DELETE' },
    token
  );
}

// ---------------------------------------------------------
// ANALYSIS PERSISTENCE
// ---------------------------------------------------------

export function listAnalyses(
  token: string,
  projectId: number
) {
  return request<Array<{
    id: number;
    project_id: number;
    research_idea: string;
    result_json: string;
    created_at: string;
  }>>(
    `/api/v1/research/analyses/${projectId}`,
    {},
    token
  );
}

// ---------------------------------------------------------
// EVIDENCE SESSIONS
// ---------------------------------------------------------

export type EvidenceSessionItem = {
  id: number;
  session_id: number;
  item_type: string;
  item_id: number;
  note: string | null;
  created_at: string;
  title: string | null;
  url: string | null;
};

export type EvidenceSession = {
  id: number;
  project_id: number;
  owner_id: number;
  title: string;
  description: string | null;
  notes: string | null;
  session_date: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  items: EvidenceSessionItem[];
};

export function listEvidenceSessions(token: string, projectId: number) {
  return request<EvidenceSession[]>(
    `/api/v1/evidence-sessions/project/${projectId}`,
    {},
    token
  );
}

export function createEvidenceSession(
  token: string,
  projectId: number,
  data: { title: string; description?: string; notes?: string; session_date?: string; status?: string }
) {
  return request<EvidenceSession>(
    `/api/v1/evidence-sessions/project/${projectId}`,
    { method: 'POST', body: JSON.stringify(data) },
    token
  );
}

export function getEvidenceSession(token: string, sessionId: number) {
  return request<EvidenceSession>(
    `/api/v1/evidence-sessions/${sessionId}`,
    {},
    token
  );
}

export function updateEvidenceSession(
  token: string,
  sessionId: number,
  data: { title?: string; description?: string; notes?: string; session_date?: string; status?: string }
) {
  return request<EvidenceSession>(
    `/api/v1/evidence-sessions/${sessionId}`,
    { method: 'PATCH', body: JSON.stringify(data) },
    token
  );
}

export function deleteEvidenceSession(token: string, sessionId: number) {
  return request<void>(
    `/api/v1/evidence-sessions/${sessionId}`,
    { method: 'DELETE' },
    token
  );
}

export function addEvidenceSessionItem(
  token: string,
  sessionId: number,
  data: { item_type: string; item_id: number; note?: string }
) {
  return request<EvidenceSessionItem>(
    `/api/v1/evidence-sessions/${sessionId}/items`,
    { method: 'POST', body: JSON.stringify(data) },
    token
  );
}

export function removeEvidenceSessionItem(token: string, sessionId: number, itemId: number) {
  return request<void>(
    `/api/v1/evidence-sessions/${sessionId}/items/${itemId}`,
    { method: 'DELETE' },
    token
  );
}

// ---------------------------------------------------------
// LITERATURE SEARCH (paginated)
// ---------------------------------------------------------

export type LiteratureSearchResponse = {
  query: string;
  results: Array<{
    title: string;
    authors: string[];
    abstract: string;
    year: number | null;
    url: string;
    doi: string;
    citation_count: number;
    venue: string;
    source: string;
    relevance_score: number;
    citations_available: boolean;
    score_explanation?: {
      citation_impact: string;
      citations: number;
      topic_relevance: string;
      recency: string;
      published: number | null;
      source: string;
    };
  }>;
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  status: string;
  source: string;
};

export function searchLiterature(
  token: string,
  query: string,
  page: number = 1,
  perPage: number = 20,
  maxResults: number = 50
) {
  const params = new URLSearchParams({
    idea: query,
    max_results: String(maxResults),
    page: String(page),
    per_page: String(perPage),
  });
  return request<LiteratureSearchResponse>(
    `/api/v1/research/search-literature?${params.toString()}`,
    { method: 'POST' },
    token
  );
}

// ---------------------------------------------------------
// PAPER DRAFTS (Paper Writing Agent)
// ---------------------------------------------------------

export type PaperDraftVersion = {
  id: number;
  draft_id: number;
  version_number: number;
  title: string;
  content: string;
  word_count: number;
  instruction: string | null;
  created_at: string;
};

export type PaperDraft = {
  id: number;
  project_id: number;
  owner_id: number;
  title: string;
  instruction: string | null;
  content: string;
  word_count: number;
  status: string;
  source_document_ids: number[];
  source_paper_ids: number[];
  current_version: number;
  created_at: string;
  updated_at: string;
  versions: PaperDraftVersion[];
};

export function listPaperDrafts(token: string, projectId: number) {
  return request<PaperDraft[]>(
    `/api/v1/paper-drafts/project/${projectId}`,
    {},
    token
  );
}

export function createPaperDraft(
  token: string,
  projectId: number,
  data: { title: string; instruction?: string; source_document_ids?: number[]; source_paper_ids?: number[] }
) {
  return request<PaperDraft>(
    `/api/v1/paper-drafts/project/${projectId}`,
    { method: 'POST', body: JSON.stringify(data) },
    token
  );
}

export function getPaperDraft(token: string, draftId: number) {
  return request<PaperDraft>(
    `/api/v1/paper-drafts/${draftId}`,
    {},
    token
  );
}

export function updatePaperDraft(token: string, draftId: number, data: { title?: string; content?: string }) {
  return request<PaperDraft>(
    `/api/v1/paper-drafts/${draftId}`,
    { method: 'PATCH', body: JSON.stringify(data) },
    token
  );
}

export function deletePaperDraft(token: string, draftId: number) {
  return request<void>(
    `/api/v1/paper-drafts/${draftId}`,
    { method: 'DELETE' },
    token
  );
}

export function generatePaperDraft(token: string, draftId: number) {
  return request<{ status: string; draft: PaperDraft; message: string }>(
    `/api/v1/paper-drafts/${draftId}/generate`,
    { method: 'POST' },
    token
  );
}

export function listDraftVersions(token: string, draftId: number) {
  return request<Array<{
    id: number;
    version_number: number;
    title: string;
    content: string;
    word_count: number;
    created_at: string;
  }>>(
    `/api/v1/paper-drafts/${draftId}/versions`,
    {},
    token
  );
}

// ---------------------------------------------------------
// RECENT PAPERS (toggle is_recent on existing Paper model)
// ---------------------------------------------------------

export function markPaperRecent(token: string, paperId: number) {
  return request<Paper>(
    `/api/v1/papers/${paperId}`,
    { method: 'PATCH', body: JSON.stringify({ is_recent: true }) },
    token
  );
}

export function unmarkPaperRecent(token: string, paperId: number) {
  return request<Paper>(
    `/api/v1/papers/${paperId}`,
    { method: 'PATCH', body: JSON.stringify({ is_recent: false }) },
    token
  );
}
