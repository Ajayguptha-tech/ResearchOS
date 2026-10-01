'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ConnectionStatus } from '../../../components/ConnectionStatus';
import {
  getMe,
  getProjectResearchPaper,
  saveProjectResearchPaper,
  updateResearchPaper,
  listProjectDocuments,
  uploadResearchDocument,
  getDocumentContent,
  summarizeDocuments,
  DocumentSummaryItem,
  listProjects,
  deleteDocument,
  deleteProject,
  listReferences,
  createReference,
  deleteReference,
  Reference,
  UserProfile,
  Project,
  ResearchPaper,
  ResearchDocument,
  Reminder,
  listReminders,
  createReminder,
  completeReminder,
  deleteReminder,
  login,
  register,
  listEvidenceSessions,
  createEvidenceSession,
  updateEvidenceSession,
  deleteEvidenceSession,
  addEvidenceSessionItem,
  removeEvidenceSessionItem,
  EvidenceSession,
  listPaperDrafts,
  createPaperDraft,
  getPaperDraft,
  updatePaperDraft,
  deletePaperDraft,
  generatePaperDraft,
  PaperDraft,
} from '../../../lib/api';

type Section = 'overview' | 'documents' | 'editor' | 'analysis' | 'references' | 'evidence' | 'reminders' | 'writing';

const SECTIONS: { key: Section; label: string; icon: string }[] = [
  { key: 'overview', label: 'Overview', icon: '◈' },
  { key: 'documents', label: 'Documents', icon: '📄' },
  { key: 'editor', label: 'Paper Editor', icon: '✏️' },
  { key: 'writing', label: 'Paper Writing Agent', icon: '🤖' },
  { key: 'analysis', label: 'AI Analysis', icon: '✦' },
  { key: 'references', label: 'References', icon: '📚' },
  { key: 'evidence', label: 'Evidence Sessions', icon: '🔍' },
  { key: 'reminders', label: 'Reminders', icon: '⏰' },
];

export default function ProjectWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.projectId);

  const [token, setToken] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Auth
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);

  // Project data
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<ResearchDocument[]>([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploading, setUploading] = useState(false);
  const [viewingDocContentId, setViewingDocContentId] = useState<number | null>(null);
  const [docContentMap, setDocContentMap] = useState<Record<number, string>>({});
  const [loadingDocContentId, setLoadingDocContentId] = useState<number | null>(null);

  // Research paper editor
  const [paper, setPaper] = useState<ResearchPaper | null>(null);
  const [paperTitle, setPaperTitle] = useState('');
  const [paperContent, setPaperContent] = useState('');
  const [savingPaper, setSavingPaper] = useState(false);
  const [paperSaved, setPaperSaved] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // AI Analysis & Document Summaries
  const [docSummaries, setDocSummaries] = useState<DocumentSummaryItem[] | null>(null);
  const [summarizingDocs, setSummarizingDocs] = useState(false);

  // Paper Writing Agent
  const [drafts, setDrafts] = useState<PaperDraft[]>([]);
  const [activeDraft, setActiveDraft] = useState<PaperDraft | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftInstruction, setDraftInstruction] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<number[]>([]);
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [draftSaving, setDraftSaving] = useState(false);

  // References
  const [references, setReferences] = useState<Reference[]>([]);
  const [refTitle, setRefTitle] = useState('');
  const [refUrl, setRefUrl] = useState('');
  const [refAuthors, setRefAuthors] = useState('');
  const [refYear, setRefYear] = useState('');
  const [refNotes, setRefNotes] = useState('');

  // Reminders
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [reminderTitle, setReminderTitle] = useState('');
  const [reminderDesc, setReminderDesc] = useState('');
  const [reminderDatetime, setReminderDatetime] = useState('');

  // Evidence Sessions
  const [evidenceSessions, setEvidenceSessions] = useState<EvidenceSession[]>([]);
  const [esTitle, setEsTitle] = useState('');
  const [esDescription, setEsDescription] = useState('');
  const [esNotes, setEsNotes] = useState('');
  const [esDate, setEsDate] = useState('');
  const [esLoading, setEsLoading] = useState(false);
  const [esEditId, setEsEditId] = useState<number | null>(null);
  const [esEditTitle, setEsEditTitle] = useState('');
  const [esEditDescription, setEsEditDescription] = useState('');
  const [esEditNotes, setEsEditNotes] = useState('');
  const [esEditDate, setEsEditDate] = useState('');
  const [esEditStatus, setEsEditStatus] = useState('');
  const [esDetailId, setEsDetailId] = useState<number | null>(null);
  const [esAddItemSessionId, setEsAddItemSessionId] = useState<number | null>(null);
  const [esAddItemType, setEsAddItemType] = useState<'reference' | 'document'>('reference');
  const [esAddItemId, setEsAddItemId] = useState('');
  const [esAddItemNote, setEsAddItemNote] = useState('');

  // === AUTH ===
  async function handleAuth(e: FormEvent) {
    e.preventDefault();
    setAuthLoading(true);
    setError('');
    try {
      const response = isRegistering
        ? await register(email, password, name)
        : await login(email, password);
      localStorage.setItem('access_token', response.access_token);
      setToken(response.access_token);
      await loadData(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setAuthLoading(false);
    }
  }

  // === LOAD ALL DATA ===
  async function loadData(accessToken: string) {
    setLoading(true);
    setError('');
    try {
      const [profile, allProjects] = await Promise.allSettled([
        getMe(accessToken),
        listProjects(accessToken),
      ]);

      // Check for auth failure
      const firstFailure = [profile, allProjects].find(
        (r): r is PromiseRejectedResult => r.status === 'rejected' && r.reason instanceof Error && (r.reason.message === 'Invalid token' || r.reason.message === 'Authentication required')
      );
      if (firstFailure) {
        localStorage.removeItem('access_token');
        setToken(null);
        setLoading(false);
        return;
      }

      if (profile.status === 'fulfilled') setUserProfile(profile.value);
      if (allProjects.status === 'fulfilled') {
        setProjects(allProjects.value);
        const found = allProjects.value.find((p) => p.id === projectId);
        if (found) {
          setProject(found);
          // Load project-specific data
          await Promise.allSettled([
            loadDocuments(accessToken, projectId),
            loadPaper(accessToken, projectId),
            loadReminders(accessToken),
            loadReferences(accessToken, projectId),
            loadEvidenceSessions(accessToken, projectId),
            loadDrafts(accessToken, projectId),
          ]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load workspace.');
    } finally {
      setLoading(false);
    }
  }

  async function loadDocuments(accessToken: string, pid: number) {
    try {
      const docs = await listProjectDocuments(accessToken, pid);
      setDocuments(docs);
    } catch {}
  }

  async function loadPaper(accessToken: string, pid: number) {
    try {
      const p = await getProjectResearchPaper(accessToken, pid);
      if (p) {
        setPaper(p);
        setPaperTitle(p.title);
        setPaperContent(p.content);
      } else {
        setPaperTitle(`Research Paper — ${project?.title || ''}`);
        setPaperContent('');
      }
    } catch {}
  }

  async function loadReminders(accessToken: string) {
    try {
      const r = await listReminders(accessToken);
      setReminders(r);
    } catch {}
  }


  async function loadReferences(accessToken: string, pid: number) {
    try {
      const refs = await listReferences(accessToken, pid);
      setReferences(refs);
    } catch {}
  }

  // === EVIDENCE SESSIONS ===
  async function loadEvidenceSessions(accessToken: string, pid: number) {
    try {
      const sessions = await listEvidenceSessions(accessToken, pid);
      setEvidenceSessions(sessions);
    } catch {}
  }

  async function handleCreateEvidenceSession(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setEsLoading(true);
    try {
      const session = await createEvidenceSession(token, projectId, {
        title: esTitle,
        description: esDescription || undefined,
        notes: esNotes || undefined,
        session_date: esDate || undefined,
      });
      setEvidenceSessions((prev) => [session, ...prev]);
      setEsTitle('');
      setEsDescription('');
      setEsNotes('');
      setEsDate('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create evidence session.');
    } finally {
      setEsLoading(false);
    }
  }

  async function handleUpdateEvidenceSession(sessionId: number) {
    if (!token) return;
    try {
      const updated = await updateEvidenceSession(token, sessionId, {
        title: esEditTitle,
        description: esEditDescription || undefined,
        notes: esEditNotes || undefined,
        session_date: esEditDate || undefined,
        status: esEditStatus || undefined,
      });
      setEvidenceSessions((prev) => prev.map((s) => s.id === sessionId ? updated : s));
      setEsEditId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update evidence session.');
    }
  }

  async function handleDeleteEvidenceSession(sessionId: number) {
    if (!token || !window.confirm('Delete this evidence session? This cannot be undone.')) return;
    try {
      await deleteEvidenceSession(token, sessionId);
      setEvidenceSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (esDetailId === sessionId) setEsDetailId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete evidence session.');
    }
  }

  async function handleAddEvidenceSessionItem(sessionId: number) {
    if (!token || !esAddItemId) return;
    try {
      const item = await addEvidenceSessionItem(token, sessionId, {
        item_type: esAddItemType,
        item_id: Number(esAddItemId),
        note: esAddItemNote || undefined,
      });
      setEvidenceSessions((prev) => prev.map((s) => {
        if (s.id !== sessionId) return s;
        return { ...s, items: [...s.items, item] };
      }));
      setEsAddItemSessionId(null);
      setEsAddItemId('');
      setEsAddItemNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add item to session.');
    }
  }

  async function handleRemoveEvidenceSessionItem(sessionId: number, itemId: number) {
    if (!token) return;
    try {
      await removeEvidenceSessionItem(token, sessionId, itemId);
      setEvidenceSessions((prev) => prev.map((s) => {
        if (s.id !== sessionId) return s;
        return { ...s, items: s.items.filter((item) => item.id !== itemId) };
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove item from session.');
    }
  }

  // === PAPER DRAFTS ===
  async function loadDrafts(accessToken: string, pid: number) {
    try {
      const d = await listPaperDrafts(accessToken, pid);
      setDrafts(d);
    } catch {}
  }

  async function handleCreateDraft(e: FormEvent) {
    e.preventDefault();
    if (!token || !draftTitle.trim()) return;
    try {
      const draft = await createPaperDraft(token, projectId, {
        title: draftTitle.trim(),
        instruction: draftInstruction.trim() || undefined,
        source_document_ids: selectedDocIds,
        source_paper_ids: selectedPaperIds,
      });
      setDrafts((prev) => [draft, ...prev]);
      setActiveDraft(draft);
      setDraftTitle('');
      setDraftInstruction('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create draft.');
    }
  }

  async function handleGenerateDraft(draftId: number) {
    if (!token) return;
    setGeneratingDraft(true);
    try {
      const result = await generatePaperDraft(token, draftId);
      setActiveDraft(result.draft);
      setDrafts((prev) => prev.map((d) => (d.id === draftId ? result.draft : d)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate draft.');
    } finally {
      setGeneratingDraft(false);
    }
  }

  async function handleSaveDraft(draftId: number) {
    if (!token || !activeDraft) return;
    setDraftSaving(true);
    try {
      const updated = await updatePaperDraft(token, draftId, {
        title: activeDraft.title,
        content: activeDraft.content,
      });
      setActiveDraft(updated);
      setDrafts((prev) => prev.map((d) => (d.id === draftId ? updated : d)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save draft.');
    } finally {
      setDraftSaving(false);
    }
  }

  async function handleDeleteDraft(draftId: number) {
    if (!token) return;
    if (!window.confirm('Delete this draft and all its versions?')) return;
    try {
      await deletePaperDraft(token, draftId);
      setDrafts((prev) => prev.filter((d) => d.id !== draftId));
      if (activeDraft?.id === draftId) setActiveDraft(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete draft.');
    }
  }

  async function handleCreateReference(e: FormEvent) {
    e.preventDefault();
    if (!token || !refTitle.trim()) return;
    try {
      const ref = await createReference(token, projectId, {
        title: refTitle.trim(),
        url: refUrl.trim() || undefined,
        authors: refAuthors.trim() || undefined,
        year: refYear ? parseInt(refYear) : undefined,
        notes: refNotes.trim() || undefined,
      });
      setReferences((prev) => [ref, ...prev]);
      setRefTitle('');
      setRefUrl('');
      setRefAuthors('');
      setRefYear('');
      setRefNotes('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create reference.');
    }
  }

  async function handleDeleteReference(id: number) {
    if (!token) return;
    try {
      await deleteReference(token, id);
      setReferences((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete reference.');
    }
  }

  async function handleDeleteDocument(docId: number) {
    if (!token || !window.confirm('Delete this document? This cannot be undone.')) return;
    try {
      await deleteDocument(token, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document.');
    }
  }

  async function handleViewDocumentContent(docId: number) {
    if (viewingDocContentId === docId) {
      setViewingDocContentId(null);
      return;
    }
    if (docContentMap[docId] !== undefined) {
      setViewingDocContentId(docId);
      return;
    }
    if (!token) return;
    setLoadingDocContentId(docId);
    try {
      const data = await getDocumentContent(token, docId);
      setDocContentMap((prev) => ({ ...prev, [docId]: data.extracted_text }));
      setViewingDocContentId(docId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve document content.');
    } finally {
      setLoadingDocContentId(null);
    }
  }

  async function handleDeleteProject() {
    if (!token || !window.confirm('Delete this project and all its data? This cannot be undone.')) return;
    try {
      await deleteProject(token, projectId);
      router.push('/workspace');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project.');
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem('access_token');
    if (!saved) {
      router.replace('/login');
      return;
    }
    setToken(saved);
    loadData(saved);
  }, [projectId]);

  // === DOCUMENT UPLOAD ===
  async function handleUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    const file = new FormData(e.currentTarget).get('document');
    if (!(file instanceof File) || file.size === 0) return;
    setUploadStatus('');
    setUploading(true);
    setError('');
    try {
      const doc = await uploadResearchDocument(token, file, undefined, projectId);
      setDocuments((prev) => [doc, ...prev]);
      setUploadStatus(`Uploaded ${doc.filename} — ${doc.extracted_characters.toLocaleString()} characters extracted`);
      e.currentTarget.reset();
    } catch (err) {
      setUploadStatus('');
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  }

  // === RESEARCH PAPER AUTOSAVE ===
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(() => {
      savePaper(true);
    }, 3000);
  }, [paperTitle, paperContent, paper, token]);

  async function savePaper(isAuto = false) {
    if (!token || !paperTitle.trim()) return;
    if (isAuto) setAutoSaving(true);
    else setSavingPaper(true);
    try {
      if (paper) {
        const updated = await updateResearchPaper(token, paper.id, { title: paperTitle, content: paperContent });
        setPaper(updated);
      } else {
        const created = await saveProjectResearchPaper(token, projectId, paperTitle, paperContent);
        setPaper(created);
      }
      setPaperSaved(true);
      setTimeout(() => setPaperSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save.');
    } finally {
      setSavingPaper(false);
      setAutoSaving(false);
    }
  }

  // === SUMMARIZE DOCUMENTS ===
  async function handleSummarizeDocuments() {
    if (!token) return;
    setSummarizingDocs(true);
    setError('');
    try {
      const res = await summarizeDocuments(token, projectId);
      setDocSummaries(res.summaries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to summarize documents.');
    } finally {
      setSummarizingDocs(false);
    }
  }

  // === REMINDERS ===
  async function handleCreateReminder(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    try {
      const r = await createReminder(token, reminderTitle, reminderDesc || null, reminderDatetime);
      setReminders((prev) => [...prev, r]);
      setReminderTitle('');
      setReminderDesc('');
      setReminderDatetime('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create reminder.');
    }
  }

  async function handleCompleteReminder(id: number) {
    if (!token) return;
    try {
      const updated = await completeReminder(token, id);
      setReminders((prev) => prev.map((r) => r.id === updated.id ? updated : r));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed.');
    }
  }

  async function handleDeleteReminder(id: number) {
    if (!token) return;
    try {
      await deleteReminder(token, id);
      setReminders((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed.');
    }
  }

  function signOut() {
    localStorage.removeItem('access_token');
    setToken(null);
    setUserProfile(null);
    router.push('/login');
  }

  function formatReminderDate(dt: string) {
    const date = new Date(dt);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diffDays === 0) return `Today, ${timeStr}`;
    if (diffDays === 1) return `Tomorrow, ${timeStr}`;
    if (diffDays < 0) return `Overdue (${Math.abs(diffDays)} days ago)`;
    return `${date.toLocaleDateString()} ${timeStr}`;
  }

  const wordCount = paperContent.trim() ? paperContent.trim().split(/\s+/).length : 0;

  // === LOADING / AUTH REDIRECT ===
  if (loading || !token) {
    return (
      <main className="research-shell workspace-page min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="research-processing-orb mx-auto" />
          <p className="mt-4 text-sm font-medium uppercase tracking-widest text-cyan-400">ResearchOS</p>
          <p className="mt-2 text-sm text-slate-400">Loading project workspace…</p>
        </div>
      </main>
    );
  }

  // === PROJECT NOT FOUND ===
  if (!project) {
    return (
      <main className="research-shell workspace-page min-h-screen bg-slate-950 p-10 text-slate-50">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-3xl font-bold">Project not found</h1>
          <p className="mt-3 text-slate-400">This project may have been deleted or you don&apos;t have access.</p>
          <button onClick={() => router.push('/workspace')} className="mt-6 rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950">← Back to Workspace</button>
        </div>
      </main>
    );
  }

  return (
    <main className="research-shell workspace-page min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto max-w-7xl p-6 sm:p-10">

        {/* HEADER */}
        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <button onClick={() => router.push('/workspace')} className="mb-2 text-xs font-medium text-cyan-400 hover:text-cyan-300">← Back to Workspace</button>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">ResearchOS</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{project.title}</h1>
            <p className="mt-1 text-sm text-slate-400">{project.domain} · {project.status}</p>
          </div>
          <div className="flex items-center gap-3">
            {userProfile && <span className="text-sm text-slate-500">{userProfile.name}</span>}
            <button onClick={signOut} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-cyan-400 hover:text-white">Sign out</button>
          </div>
        </header>

        <div className="mt-4">
          <ConnectionStatus />
        </div>

        {error && (
          <div role="alert" className="mt-4 rounded-lg border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">{error}</div>
        )}

        {/* SIDEBAR + CONTENT */}
        <div className="mt-8 grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">

          {/* Sidebar */}
          <nav className="space-y-1">
            {SECTIONS.map((s) => (
              <button
                key={s.key}
                onClick={() => setActiveSection(s.key)}
                className={`w-full rounded-lg px-4 py-2.5 text-left text-sm font-medium transition ${activeSection === s.key ? 'bg-[rgba(105,76,197,0.1)] text-[#664bc5]' : 'text-slate-400 hover:bg-[rgba(105,76,197,0.05)] hover:text-slate-200'}`}
              >
                <span className="mr-2">{s.icon}</span>
                {s.label}
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className="min-w-0">

            {/* === OVERVIEW === */}
            {activeSection === 'overview' && (
              <section className="space-y-6">
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Project Overview</h2>
                    <button onClick={handleDeleteProject} className="rounded-lg border border-[#e7e2fa] px-3 py-1.5 text-xs font-medium transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>Delete Project</button>
                  </div>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                    <div className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4">
                      <p className="text-xs font-medium text-slate-400">Documents</p>
                      <p className="mt-1 text-2xl font-bold" style={{ color: '#6549c8' }}>{documents.length}</p>
                    </div>
                    <div className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4">
                      <p className="text-xs font-medium text-slate-400">References</p>
                      <p className="mt-1 text-2xl font-bold" style={{ color: '#6549c8' }}>{references.length}</p>
                    </div>
                    <div className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4">
                      <p className="text-xs font-medium text-slate-400">Evidence Sessions</p>
                      <p className="mt-1 text-2xl font-bold" style={{ color: '#6549c8' }}>{evidenceSessions.length}</p>
                    </div>
                    <div className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4">
                      <p className="text-xs font-medium text-slate-400">Paper Words</p>
                      <p className="mt-1 text-2xl font-bold" style={{ color: '#6549c8' }}>{paper?.word_count || 0}</p>
                    </div>
                    <div className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4">
                      <p className="text-xs font-medium text-slate-400">Reminders</p>
                      <p className="mt-1 text-2xl font-bold" style={{ color: '#6549c8' }}>{reminders.filter((r) => r.status === 'pending').length}</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h3 className="text-lg font-semibold" style={{ color: '#1b2440' }}>Research Workflow</h3>
                  <ol className="mt-4 research-stepper">
                    {['Literature Search', 'Paper Analysis', 'Gap Analysis', 'Dataset Recommendation', 'Experiment Planning', 'Research Roadmap'].map((stage, i) => (
                      <li key={stage}><span>{i + 1}</span>{stage}</li>
                    ))}
                  </ol>
                </div>
              </section>
            )}

            {/* === DOCUMENTS === */}
            {activeSection === 'documents' && (
              <section className="space-y-6">
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Source Documents</h2>
                  <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Upload research papers, articles, and documents for AI-powered analysis.</p>

                  <form onSubmit={handleUpload} className="mt-5">
                    <div className="rounded-xl border-2 border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center transition hover:border-[#7c60d6]">
                      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: 'rgba(105, 76, 197, 0.08)' }}>
                        <span style={{ color: '#664bc5', fontSize: '1.3rem' }}>📎</span>
                      </div>
                      <p className="text-sm font-semibold" style={{ color: '#1b2440' }}>Upload source documents</p>
                      <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, HTML, JSON, XML, PNG, JPG</p>
                      <input name="document" required type="file" accept=".txt,.md,.markdown,.pdf,.docx,.csv,.xlsx,.xls,.pptx,.html,.htm,.json,.xml,.png,.jpg,.jpeg,.webp" className="mt-4 block w-full text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-[#6247bf] file:px-4 file:py-2 file:text-white file:font-medium" />
                    </div>
                    <button type="submit" disabled={uploading} className="mt-3 w-full rounded-xl bg-[#6247bf] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50">
                      {uploading ? 'Uploading…' : 'Upload Document'}
                    </button>
                  </form>
                  {uploadStatus && <p className="mt-3 text-xs font-medium" style={{ color: '#3a8c6a' }}>{uploadStatus}</p>}
                </div>

                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h3 className="text-lg font-semibold" style={{ color: '#1b2440' }}>Uploaded Documents ({documents.length})</h3>
                  {documents.length === 0 ? (
                    <div className="mt-4 rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center">
                      <p className="text-sm font-medium" style={{ color: '#1b2440' }}>No documents yet</p>
                      <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>Upload your first source document above.</p>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {documents.map((doc) => (
                        <article key={doc.id} className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4 transition hover:border-[#7c60d6]">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold truncate" style={{ color: '#1b2440' }}>{doc.filename}</p>
                              <p className="text-xs" style={{ color: '#8790a4' }}>{doc.extracted_characters.toLocaleString()} characters extracted · {doc.content_type}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleViewDocumentContent(doc.id)}
                                className="shrink-0 rounded-lg border border-[#e0d9f4] bg-white px-2.5 py-1 text-xs font-medium transition hover:border-[#7c60d6]"
                                style={{ color: '#6247bf' }}
                              >
                                {loadingDocContentId === doc.id
                                  ? 'Loading…'
                                  : viewingDocContentId === doc.id
                                  ? 'Hide Text'
                                  : 'View Extracted Text'}
                              </button>
                              <span className="shrink-0 rounded-full bg-[rgba(58,140,106,0.1)] px-3 py-1 text-xs font-medium" style={{ color: '#3a8c6a' }}>✓ Ready</span>
                              <button onClick={() => handleDeleteDocument(doc.id)} className="shrink-0 rounded-lg border border-[#e7e2fa] px-2 py-1 text-xs transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>✕</button>
                            </div>
                          </div>
                          {viewingDocContentId === doc.id && (
                            <div className="mt-3 border-t border-[#e7e2fa] pt-3">
                              <div className="flex items-center justify-between pb-1.5">
                                <span className="text-xs font-semibold" style={{ color: '#6247bf' }}>
                                  Extracted Content Preview ({doc.extracted_characters.toLocaleString()} chars)
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setViewingDocContentId(null)}
                                  className="text-xs hover:underline"
                                  style={{ color: '#8790a4' }}
                                >
                                  Close
                                </button>
                              </div>
                              <div className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg border border-[#e0d9f4] bg-white p-3 font-mono text-xs text-[#1b2440]">
                                {docContentMap[doc.id] || 'No extracted text found.'}
                              </div>
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* === PAPER EDITOR === */}
            {activeSection === 'editor' && (
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Research Paper Editor</h2>
                    <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Write and edit your research paper directly in ResearchOS.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: '#8790a4' }}>{wordCount} words</span>
                    {autoSaving && <span className="text-xs" style={{ color: '#664bc5' }}>Auto-saving…</span>}
                    {paperSaved && <span className="text-xs" style={{ color: '#3a8c6a' }}>✓ Saved</span>}
                    <button onClick={() => savePaper(false)} disabled={savingPaper || !paperTitle.trim()} className="rounded-xl bg-[#6247bf] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50">
                      {savingPaper ? 'Saving…' : 'Save'}
                    </button>
                  </div>
                </div>

                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <input
                    value={paperTitle}
                    onChange={(e) => setPaperTitle(e.target.value)}
                    placeholder="Research Paper Title"
                    className="w-full border-none bg-transparent text-2xl font-bold outline-none placeholder:text-[#a1a9bb]"
                    style={{ color: '#1b2440' }}
                  />

                  <div className="mt-6 space-y-1">
                    {['Abstract', 'Introduction', 'Literature Review', 'Methodology', 'Results', 'Discussion', 'Conclusion', 'References'].map((section) => (
                      <button
                        key={section}
                        onClick={() => {
                          const marker = `## ${section}\n`;
                          if (!paperContent.includes(marker)) {
                            setPaperContent((prev) => prev + `\n\n${marker}\n`);
                          }
                          // Scroll to section in textarea
                        }}
                        className="rounded-lg px-3 py-1.5 text-xs font-medium transition hover:bg-[rgba(105,76,197,0.06)]"
                        style={{ color: '#664bc5' }}
                      >
                        + {section}
                      </button>
                    ))}
                  </div>

                  <textarea
                    value={paperContent}
                    onChange={(e) => {
                      setPaperContent(e.target.value);
                      scheduleAutoSave();
                    }}
                    placeholder="Start writing your research paper…&#10;&#10;Use ## headings to structure sections (e.g., ## Abstract, ## Introduction).&#10;&#10;Your work is auto-saved every 3 seconds."
                    rows={24}
                    className="mt-4 w-full resize-y rounded-xl border border-[#e0d9f4] bg-white px-5 py-4 text-sm leading-relaxed outline-none transition focus:border-[#7c60d6]"
                    style={{ color: '#1d2742', minHeight: '400px', fontFamily: 'Georgia, serif' }}
                  />
                </div>
              </section>
            )}

            {/* === AI ANALYSIS === */}
            {activeSection === 'analysis' && (
              <section className="space-y-6">
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                      <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>AI Research Analysis</h2>
                      <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Analyze project documents and synthesize evidence-backed insights.</p>
                    </div>
                    <button
                      onClick={handleSummarizeDocuments}
                      disabled={summarizingDocs || documents.length === 0}
                      className="inline-flex items-center justify-center rounded-xl bg-[#6247bf] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#5538a8] disabled:opacity-50"
                    >
                      {summarizingDocs ? 'Summarizing Documents…' : `Summarize Documents (${documents.length})`}
                    </button>
                  </div>

                  {/* Clean Idle State */}
                  {!docSummaries && !summarizingDocs && (
                    <div className="mt-6 rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center">
                      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(105,76,197,0.1)] text-xl" style={{ color: '#664bc5' }}>✦</div>
                      <h3 className="text-base font-semibold" style={{ color: '#1b2440' }}>Summarize Project Documents</h3>
                      <p className="mt-1 text-sm max-w-md mx-auto" style={{ color: '#68728a' }}>
                        Click <strong>Summarize Documents</strong> to generate concise, grounded summaries, key findings, and methodology from this project&apos;s uploaded documents.
                      </p>
                      <div className="mt-5 flex flex-wrap justify-center gap-3">
                        <button
                          onClick={handleSummarizeDocuments}
                          disabled={documents.length === 0}
                          className="rounded-xl bg-[#6247bf] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50"
                        >
                          Summarize Documents ({documents.length})
                        </button>
                      </div>
                      {documents.length === 0 && (
                        <p className="mt-3 text-xs text-amber-600">
                          Upload documents in the <strong>Documents</strong> tab to enable document summarization.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Loading states */}
                  {summarizingDocs && (
                    <div className="mt-6 rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-6 text-center">
                      <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#e0d9f4] border-t-[#6247bf]" />
                      <p className="text-sm font-semibold" style={{ color: '#1b2440' }}>Summarizing project documents…</p>
                      <p className="mt-1 text-xs" style={{ color: '#68728a' }}>Extracting title, summary, key findings, and methodology from project documents only.</p>
                    </div>
                  )}

                  {/* Scoped Document Summaries Result */}
                  {docSummaries && !summarizingDocs && (
                    <div className="mt-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold" style={{ color: '#1b2440' }}>
                          📄 Document Summaries ({docSummaries.length})
                        </h3>
                        <button
                          onClick={() => setDocSummaries(null)}
                          className="text-xs font-medium text-slate-400 hover:text-slate-600"
                        >
                          Clear
                        </button>
                      </div>
                      {docSummaries.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-6 text-center">
                          <p className="text-sm" style={{ color: '#68728a' }}>No documents found in this project to summarize.</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {docSummaries.map((ds) => (
                            <div key={ds.document_id} className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-5">
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <h4 className="font-semibold text-sm" style={{ color: '#1b2440' }}>{ds.title}</h4>
                                  <p className="mt-0.5 text-xs text-slate-400">{ds.filename} · {ds.extracted_characters.toLocaleString()} characters extracted</p>
                                </div>
                                <span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">Project Doc #{ds.document_id}</span>
                              </div>
                              {ds.summary && (
                                <div className="mt-3">
                                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Summary</p>
                                  <p className="mt-1 text-xs leading-relaxed" style={{ color: '#4e5871' }}>{ds.summary}</p>
                                </div>
                              )}
                              {ds.key_findings && ds.key_findings.length > 0 && (
                                <div className="mt-3">
                                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Key Findings</p>
                                  <ul className="mt-1 space-y-1">
                                    {ds.key_findings.map((f, i) => (
                                      <li key={i} className="flex items-start gap-2 text-xs" style={{ color: '#4e5871' }}>
                                        <span className="mt-0.5 text-[#664bc5]">•</span>
                                        <span>{f}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {ds.methodology && ds.methodology.length > 0 && (
                                <div className="mt-3">
                                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Methodology</p>
                                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                                    {ds.methodology.map((m, i) => (
                                      <span key={i} className="rounded-full bg-[rgba(105,76,197,0.08)] px-2.5 py-0.5 text-xs font-medium" style={{ color: '#664bc5' }}>
                                        {m}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}



            {/* === REFERENCES === */}
            {activeSection === 'references' && (
              <section className="space-y-6">
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>References</h2>
                  <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Add and manage references for this project.</p>

                  <form onSubmit={handleCreateReference} className="mt-5 grid gap-3 sm:grid-cols-2">
                    <input required value={refTitle} onChange={(e) => setRefTitle(e.target.value)} placeholder="Reference title *" className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input value={refUrl} onChange={(e) => setRefUrl(e.target.value)} placeholder="URL (optional)" className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input value={refAuthors} onChange={(e) => setRefAuthors(e.target.value)} placeholder="Authors (optional)" className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input value={refYear} onChange={(e) => setRefYear(e.target.value)} placeholder="Year" type="number" min="1900" max="2100" className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input value={refNotes} onChange={(e) => setRefNotes(e.target.value)} placeholder="Notes (optional)" className="sm:col-span-2 rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <button type="submit" className="sm:col-span-2 rounded-xl bg-[#6247bf] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#5538a8]">Add Reference</button>
                  </form>
                </div>

                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h3 className="text-lg font-semibold" style={{ color: '#1b2440' }}>Saved References ({references.length})</h3>
                  {references.length === 0 ? (
                    <div className="mt-4 rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center">
                      <p className="text-sm font-medium" style={{ color: '#1b2440' }}>No references yet</p>
                      <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>Add your first reference above.</p>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {references.map((ref) => (
                        <article key={ref.id} className="flex items-start justify-between rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-4 transition hover:border-[#7c60d6]">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold" style={{ color: '#1b2440' }}>{ref.title}</p>
                            {ref.authors && <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>{ref.authors}{ref.year ? ` (${ref.year})` : ''}</p>}
                            {ref.notes && <p className="mt-1 text-xs" style={{ color: '#68728a' }}>{ref.notes}</p>}
                            {ref.url && <a href={ref.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-xs font-medium" style={{ color: '#664bc5' }}>Open link →</a>}
                          </div>
                          <button onClick={() => handleDeleteReference(ref.id)} className="shrink-0 rounded-lg border border-[#e7e2fa] px-2 py-1 text-xs transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>✕</button>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* === EVIDENCE SESSIONS === */}
            {activeSection === 'evidence' && (
              <section className="space-y-6">
                {/* Create form */}
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Evidence Sessions</h2>
                  <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Create and manage evidence-gathering sessions for this project.</p>

                  <form onSubmit={handleCreateEvidenceSession} className="mt-5 grid gap-3 sm:grid-cols-2">
                    <input required value={esTitle} onChange={(e) => setEsTitle(e.target.value)} placeholder="Session title *" className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input type="date" value={esDate} onChange={(e) => setEsDate(e.target.value)} className="rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <input value={esDescription} onChange={(e) => setEsDescription(e.target.value)} placeholder="Description (optional)" className="sm:col-span-2 rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <textarea value={esNotes} onChange={(e) => setEsNotes(e.target.value)} placeholder="Notes (optional)" rows={3} className="sm:col-span-2 resize-none rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <button disabled={esLoading} type="submit" className="sm:col-span-2 rounded-xl bg-[#6247bf] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50">
                      {esLoading ? 'Creating...' : 'Create Evidence Session'}
                    </button>
                  </form>
                </div>

                {/* Sessions list */}
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h3 className="text-lg font-semibold" style={{ color: '#1b2440' }}>Sessions ({evidenceSessions.length})</h3>
                  {evidenceSessions.length === 0 ? (
                    <div className="mt-4 rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center">
                      <p className="text-sm font-medium" style={{ color: '#1b2440' }}>No evidence sessions yet</p>
                      <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>Create your first session above.</p>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-4">
                      {evidenceSessions.map((session) => (
                        <article key={session.id} className="rounded-xl border border-[#e7e2fa] bg-[#fdfcff] p-5 transition hover:border-[#7c60d6]">
                          {/* Header */}
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0">
                              {esEditId === session.id ? (
                                <div className="space-y-2">
                                  <input value={esEditTitle} onChange={(e) => setEsEditTitle(e.target.value)} className="w-full rounded-lg border border-[#e0d9f4] bg-white px-3 py-2 text-sm font-semibold outline-none focus:border-[#7c60d6]" style={{ color: '#1b2440' }} />
                                  <input value={esEditDescription} onChange={(e) => setEsEditDescription(e.target.value)} placeholder="Description" className="w-full rounded-lg border border-[#e0d9f4] bg-white px-3 py-2 text-sm outline-none focus:border-[#7c60d6]" style={{ color: '#1d2742' }} />
                                  <textarea value={esEditNotes} onChange={(e) => setEsEditNotes(e.target.value)} placeholder="Notes" rows={3} className="w-full resize-none rounded-lg border border-[#e0d9f4] bg-white px-3 py-2 text-sm outline-none focus:border-[#7c60d6]" style={{ color: '#1d2742' }} />
                                  <div className="flex gap-2">
                                    <input type="date" value={esEditDate} onChange={(e) => setEsEditDate(e.target.value)} className="rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none" style={{ color: '#1d2742' }} />
                                    <select value={esEditStatus} onChange={(e) => setEsEditStatus(e.target.value)} className="rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none" style={{ color: '#1d2742' }}>
                                      <option value="active">Active</option>
                                      <option value="completed">Completed</option>
                                      <option value="archived">Archived</option>
                                    </select>
                                  </div>
                                  <div className="flex gap-2">
                                    <button onClick={() => handleUpdateEvidenceSession(session.id)} className="rounded-lg bg-[#6247bf] px-3 py-1.5 text-xs font-semibold text-white">Save</button>
                                    <button onClick={() => setEsEditId(null)} className="rounded-lg border border-[#e0d9f4] px-3 py-1.5 text-xs" style={{ color: '#8790a4' }}>Cancel</button>
                                  </div>
                                </div>
                              ) : (
                                <>
                                  <h4 className="font-semibold" style={{ color: '#1b2440' }}>{session.title}</h4>
                                  {session.description && <p className="mt-1 text-sm" style={{ color: '#68728a' }}>{session.description}</p>}
                                  {session.notes && <p className="mt-1 text-xs whitespace-pre-wrap" style={{ color: '#8790a4' }}>{session.notes}</p>}
                                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs" style={{ color: '#8790a4' }}>
                                    <span className={`rounded-full px-2 py-0.5 font-medium ${session.status === 'completed' ? 'bg-emerald-50 text-emerald-700' : session.status === 'archived' ? 'bg-slate-100 text-slate-500' : 'bg-violet-50 text-violet-700'}`}>{session.status}</span>
                                    {session.session_date && <span>Date: {new Date(session.session_date).toLocaleDateString()}</span>}
                                    <span>{session.items.length} item(s)</span>
                                    <span>Created {new Date(session.created_at).toLocaleDateString()}</span>
                                  </div>
                                </>
                              )}
                            </div>
                            {esEditId !== session.id && (
                              <div className="flex shrink-0 gap-1">
                                <button onClick={() => { setEsEditId(session.id); setEsEditTitle(session.title); setEsEditDescription(session.description || ''); setEsEditNotes(session.notes || ''); setEsEditDate(session.session_date ? session.session_date.split('T')[0] : ''); setEsEditStatus(session.status); }} className="rounded-lg border border-[#e0d9f4] px-2 py-1 text-xs transition hover:border-[#7c60d6]" style={{ color: '#664bc5' }}>Edit</button>
                                <button onClick={() => handleDeleteEvidenceSession(session.id)} className="rounded-lg border border-[#e7e2fa] px-2 py-1 text-xs transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>Delete</button>
                              </div>
                            )}
                          </div>

                          {/* Attached items */}
                          <div className="mt-4">
                            {session.items.length > 0 && (
                              <div className="space-y-1">
                                {session.items.map((item) => (
                                  <div key={item.id} className="flex items-center justify-between rounded-lg bg-white border border-[#e0d9f4] px-3 py-2">
                                    <div className="min-w-0">
                                      <span className="text-xs font-medium rounded-full px-1.5 py-0.5 mr-2" style={{ background: item.item_type === 'reference' ? '#ede9fe' : '#e0f2fe', color: item.item_type === 'reference' ? '#6d28d9' : '#0369a1' }}>{item.item_type === 'reference' ? 'Ref' : 'Doc'}</span>
                                      <span className="text-sm" style={{ color: '#1b2440' }}>{item.title || `#${item.item_id}`}</span>
                                      {item.url && <a href={item.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-xs" style={{ color: '#664bc5' }}>↗</a>}
                                      {item.note && <span className="ml-2 text-xs" style={{ color: '#8790a4' }}>— {item.note}</span>}
                                    </div>
                                    <button onClick={() => handleRemoveEvidenceSessionItem(session.id, item.id)} className="shrink-0 rounded-lg border border-[#e7e2fa] px-1.5 py-0.5 text-xs transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>✕</button>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Add item form */}
                            {esAddItemSessionId === session.id ? (
                              <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg bg-white border border-dashed border-[#e0d9f4] p-3">
                                <select value={esAddItemType} onChange={(e) => { setEsAddItemType(e.target.value as 'reference' | 'document'); setEsAddItemId(''); }} className="rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none" style={{ color: '#1d2742' }}>
                                  <option value="reference">Reference</option>
                                  <option value="document">Document</option>
                                </select>
                                {esAddItemType === 'reference' && references.length > 0 ? (
                                  <select value={esAddItemId} onChange={(e) => setEsAddItemId(e.target.value)} className="rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none max-w-xs" style={{ color: '#1d2742' }}>
                                    <option value="">Select a reference...</option>
                                    {references.map((r) => <option key={r.id} value={r.id}>#{r.id} — {r.title}</option>)}
                                  </select>
                                ) : esAddItemType === 'document' && documents.length > 0 ? (
                                  <select value={esAddItemId} onChange={(e) => setEsAddItemId(e.target.value)} className="rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none max-w-xs" style={{ color: '#1d2742' }}>
                                    <option value="">Select a document...</option>
                                    {documents.map((d) => <option key={d.id} value={d.id}>#{d.id} — {d.filename}</option>)}
                                  </select>
                                ) : (
                                  <input value={esAddItemId} onChange={(e) => setEsAddItemId(e.target.value)} placeholder={esAddItemType === 'reference' ? 'Reference ID' : 'Document ID'} className="w-24 rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none" style={{ color: '#1d2742' }} />
                                )}
                                <input value={esAddItemNote} onChange={(e) => setEsAddItemNote(e.target.value)} placeholder="Note (optional)" className="flex-1 rounded-lg border border-[#e0d9f4] bg-white px-3 py-1.5 text-xs outline-none" style={{ color: '#1d2742' }} />
                                <button disabled={!esAddItemId} onClick={() => handleAddEvidenceSessionItem(session.id)} className="rounded-lg bg-[#6247bf] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Add</button>
                                <button onClick={() => { setEsAddItemSessionId(null); setEsAddItemId(''); }} className="rounded-lg border border-[#e0d9f4] px-3 py-1.5 text-xs" style={{ color: '#8790a4' }}>Cancel</button>
                              </div>
                            ) : (
                              <button onClick={() => setEsAddItemSessionId(session.id)} className="mt-3 text-xs font-medium transition" style={{ color: '#664bc5' }}>+ Add Evidence / Reference</button>
                            )}
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* === PAPER WRITING AGENT === */}
            {activeSection === 'writing' && (
              <section className="space-y-6">
                {/* Create new draft */}
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Paper Writing Agent</h2>
                  <p className="mt-1 text-sm" style={{ color: '#68728a' }}>
                    Generate research paper drafts grounded in your selected source documents and papers.
                  </p>

                  <form onSubmit={handleCreateDraft} className="mt-5 space-y-3">
                    <input required value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} placeholder="Paper title *" className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />
                    <textarea value={draftInstruction} onChange={(e) => setDraftInstruction(e.target.value)} placeholder="Instructions: e.g., 'Write an IEEE-style paper focusing on the research gap and methodology. Use academic tone.'" rows={3} className="w-full resize-none rounded-xl border border-[#e0d9f4] bg-white px-4 py-2.5 text-sm outline-none" style={{ color: '#1d2742' }} />

                    {/* Source Document Selection */}
                    <div className="rounded-xl border border-[#e0d9f4] bg-[#fdfcff] p-4">
                      <p className="text-xs font-semibold" style={{ color: '#1b2440' }}>Source Documents</p>
                      <p className="mt-0.5 text-[10px]" style={{ color: '#8790a4' }}>Select which uploaded documents the agent may use</p>
                      <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                        {documents.length === 0 ? (
                          <p className="text-xs" style={{ color: '#8790a4' }}>No documents uploaded yet.</p>
                        ) : documents.map((doc) => (
                          <label key={doc.id} className="flex items-center gap-2 cursor-pointer rounded-lg px-2 py-1 hover:bg-white">
                            <input type="checkbox" checked={selectedDocIds.includes(doc.id)} onChange={(e) => {
                              if (e.target.checked) setSelectedDocIds((prev) => [...prev, doc.id]);
                              else setSelectedDocIds((prev) => prev.filter((id) => id !== doc.id));
                            }} className="accent-[#6247bf]" />
                            <span className="text-xs truncate" style={{ color: '#1b2440' }}>{doc.filename}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Reference Selection */}
                    <div className="rounded-xl border border-[#e0d9f4] bg-[#fdfcff] p-4">
                      <p className="text-xs font-semibold" style={{ color: '#1b2440' }}>References</p>
                      <p className="mt-0.5 text-[10px]" style={{ color: '#8790a4' }}>Select references to include in the paper</p>
                      <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                        {references.length === 0 ? (
                          <p className="text-xs" style={{ color: '#8790a4' }}>No references added yet.</p>
                        ) : references.map((ref) => (
                          <label key={ref.id} className="flex items-center gap-2 cursor-pointer rounded-lg px-2 py-1 hover:bg-white">
                            <input type="checkbox" checked={selectedPaperIds.includes(ref.id)} onChange={(e) => {
                              if (e.target.checked) setSelectedPaperIds((prev) => [...prev, ref.id]);
                              else setSelectedPaperIds((prev) => prev.filter((id) => id !== ref.id));
                            }} className="accent-[#6247bf]" />
                            <span className="text-xs truncate" style={{ color: '#1b2440' }}>{ref.title}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <button disabled={!draftTitle.trim()} className="w-full rounded-xl bg-[#6247bf] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50">
                      Create Draft
                    </button>
                  </form>
                </div>

                {/* Drafts list + editor */}
                <div className="rounded-2xl border border-[#e7e2fa] bg-white p-6" style={{ boxShadow: '0 12px 30px rgba(62, 42, 132, 0.055)' }}>
                  <h3 className="text-lg font-semibold" style={{ color: '#1b2440' }}>Drafts ({drafts.length})</h3>
                  {drafts.length === 0 ? (
                    <div className="mt-4 rounded-xl border border-dashed border-[#e0d9f4] bg-[#fdfcff] p-8 text-center">
                      <p className="text-sm font-medium" style={{ color: '#1b2440' }}>No drafts yet</p>
                      <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>Create your first draft above.</p>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-3">
                      {drafts.map((draft) => (
                        <article key={draft.id} className={`rounded-xl border p-5 transition ${activeDraft?.id === draft.id ? 'border-[#7c60d6] bg-[#fdfcff]' : 'border-[#e7e2fa] bg-[#fdfcff] hover:border-[#7c60d6]'}`}>
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h4 className="font-semibold" style={{ color: '#1b2440' }}>{draft.title}</h4>
                              <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>
                                v{draft.current_version} · {draft.word_count} words · {new Date(draft.updated_at).toLocaleDateString()}
                              </p>
                              {draft.instruction && <p className="mt-1 text-xs italic" style={{ color: '#68728a' }}>&ldquo;{draft.instruction}&rdquo;</p>}
                            </div>
                            <div className="flex shrink-0 gap-1">
                              <button onClick={() => setActiveDraft(activeDraft?.id === draft.id ? null : draft)} className="rounded-lg border border-[#e0d9f4] px-2 py-1 text-xs" style={{ color: '#664bc5' }}>
                                {activeDraft?.id === draft.id ? 'Close' : 'Open'}
                              </button>
                              <button onClick={() => handleDeleteDraft(draft.id)} className="rounded-lg border border-[#e7e2fa] px-2 py-1 text-xs transition hover:border-[#d66060] hover:text-[#d66060]" style={{ color: '#8790a4' }}>Delete</button>
                            </div>
                          </div>

                          {/* Expanded draft editor */}
                          {activeDraft?.id === draft.id && (
                            <div className="mt-4 space-y-3 border-t border-[#e0d9f4] pt-4">
                              <div className="flex items-center gap-2">
                                <button onClick={() => handleGenerateDraft(draft.id)} disabled={generatingDraft} className="rounded-xl bg-[#6247bf] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#5538a8] disabled:opacity-50">
                                  {generatingDraft ? 'Generating...' : '🤖 Generate / Regenerate Draft'}
                                </button>
                                <button onClick={() => handleSaveDraft(draft.id)} disabled={draftSaving} className="rounded-xl border border-[#e0d9f4] px-4 py-2 text-xs font-medium transition hover:border-[#7c60d6]" style={{ color: '#664bc5' }}>
                                  {draftSaving ? 'Saving...' : 'Save Draft'}
                                </button>
                                {draft.versions.length > 0 && (
                                  <span className="text-[10px]" style={{ color: '#8790a4' }}>{draft.versions.length} version(s) saved</span>
                                )}
                              </div>

                              <textarea
                                value={activeDraft.content}
                                onChange={(e) => setActiveDraft({ ...activeDraft, content: e.target.value })}
                                rows={24}
                                className="w-full resize-y rounded-xl border border-[#e0d9f4] bg-white px-5 py-4 text-sm leading-relaxed outline-none transition focus:border-[#7c60d6]"
                                style={{ color: '#1d2742', minHeight: '400px', fontFamily: 'Georgia, serif' }}
                                placeholder="Generated paper content will appear here after clicking Generate..."
                              />

                              {/* Version history */}
                              {draft.versions.length > 0 && (
                                <div className="rounded-xl border border-[#e0d9f4] bg-[#fdfcff] p-4">
                                  <p className="text-xs font-semibold" style={{ color: '#1b2440' }}>Version History</p>
                                  <div className="mt-2 space-y-1">
                                    {draft.versions.map((v) => (
                                      <div key={v.id} className="flex items-center justify-between rounded-lg bg-white px-3 py-1.5">
                                        <span className="text-xs" style={{ color: '#68728a' }}>v{v.version_number} — {v.word_count} words — {new Date(v.created_at).toLocaleString()}</span>
                                        <button onClick={() => setActiveDraft({ ...activeDraft, content: v.content, current_version: v.version_number })} className="text-[10px] font-medium" style={{ color: '#664bc5' }}>Restore</button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* === REMINDERS === */}
            {activeSection === 'reminders' && (
              <section className="space-y-6">
                <div className="flex items-end justify-between">
                  <div>
                    <h2 className="text-xl font-semibold" style={{ color: '#1b2440' }}>Research Reminders</h2>
                    <p className="mt-1 text-sm" style={{ color: '#68728a' }}>Stay on track with your research tasks and deadlines.</p>
                  </div>
                  <span className="text-sm text-slate-500">{reminders.filter((r) => r.status === 'pending').length} upcoming</span>
                </div>

                <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                  <div className="space-y-3">
                    {reminders.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-[#e0d9f4] bg-white p-8 text-center">
                        <p className="text-sm font-semibold" style={{ color: '#1b2440' }}>No reminders yet</p>
                        <p className="mt-1 text-xs" style={{ color: '#8790a4' }}>Create your first reminder to stay organized.</p>
                      </div>
                    ) : reminders.map((r) => {
                      const isOverdue = r.status !== 'completed' && new Date(r.reminder_datetime) < new Date();
                      const isDueSoon = !isOverdue && r.status !== 'completed' && (new Date(r.reminder_datetime).getTime() - Date.now()) < 86400000;
                      const sc = r.status === 'completed' ? 'completed' : isOverdue ? 'overdue' : isDueSoon ? 'due-soon' : 'upcoming';
                      return (
                        <article key={r.id} className={`reminder-card status-${sc}`}>
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0">
                              <h3 className="font-semibold" style={{ color: '#1b2440' }}>{r.title}</h3>
                              {r.description && <p className="mt-1 text-sm text-slate-400">{r.description}</p>}
                              <p className="mt-2 text-xs text-slate-500">
                                {r.status === 'completed' ? `Completed ${new Date(r.updated_at).toLocaleDateString()}` : formatReminderDate(r.reminder_datetime)}
                              </p>
                            </div>
                            <span className={`reminder-status-badge shrink-0 ${sc}`}>
                              {r.status === 'completed' ? '✓ Completed' : isOverdue ? 'Overdue' : isDueSoon ? 'Due soon' : 'Upcoming'}
                            </span>
                          </div>
                          {r.status !== 'completed' && (
                            <div className="mt-3 flex gap-2">
                              <button onClick={() => handleCompleteReminder(r.id)} className="rounded-lg px-3 py-1.5 text-xs font-semibold text-white" style={{ background: 'linear-gradient(135deg, #6d4fd2, #8d70ed)' }}>Mark complete</button>
                              <button onClick={() => handleDeleteReminder(r.id)} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:text-[#d66060]">Delete</button>
                            </div>
                          )}
                        </article>
                      );
                    })}
                  </div>

                  <form onSubmit={handleCreateReminder} className="h-fit rounded-xl border border-[#e7e2fa] bg-white p-5" style={{ boxShadow: '0 10px 28px rgba(62, 42, 132, 0.055)' }}>
                    <h3 className="font-semibold" style={{ color: '#1b2440' }}>Add a reminder</h3>
                    <div className="mt-4 space-y-3">
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-500">Title</label>
                        <input required value={reminderTitle} onChange={(e) => setReminderTitle(e.target.value)} placeholder="e.g., Review literature" className="w-full rounded-lg border border-[#e0d9f4] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#7c60d6]" style={{ color: '#1d2742' }} />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-500">Notes</label>
                        <textarea value={reminderDesc} onChange={(e) => setReminderDesc(e.target.value)} placeholder="Optional" rows={2} className="w-full resize-none rounded-lg border border-[#e0d9f4] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#7c60d6]" style={{ color: '#1d2742' }} />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-500">Date & time</label>
                        <input required type="datetime-local" value={reminderDatetime} onChange={(e) => setReminderDatetime(e.target.value)} className="w-full rounded-lg border border-[#e0d9f4] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#7c60d6]" style={{ color: '#1d2742' }} />
                      </div>
                      <button className="w-full rounded-lg px-4 py-2.5 text-sm font-semibold text-white" style={{ background: 'linear-gradient(135deg, #6d4fd2, #8d70ed)' }}>Create reminder</button>
                    </div>
                  </form>
                </div>
              </section>
            )}

          </div>
        </div>

      </div>



      {/* Footer Credit */}
      <footer className="fixed bottom-2 right-5 z-30 select-none pointer-events-none text-right">
        <p className="text-[11px] font-semibold tracking-wide text-slate-500/50">
          ResearchOS
        </p>
        <p className="text-[10px] text-slate-500/35">
          Designed by Ajay Guptha | Dept. of CSE
        </p>
      </footer>
    </main>
  );
}
