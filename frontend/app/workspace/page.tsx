'use client';

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useRouter } from 'next/navigation';
import { ConnectionStatus } from '../../components/ConnectionStatus';

import {
  analyzeResearch,
  completeFollowUp,
  createFollowUp,
  createPaper,
  updatePaper,
  deletePaper,
  createReminder,
  cancelReminder,
  updateReminder,
  completeReminder,
  deleteReminder,
  deleteDocument,
  getMe,
  listNotifications,
  listFollowUps,
  listPapers,
  listProjects,
  createProject,
  listDocuments,
  listReminders,
  login,
  markNotificationRead,
  Notification,
  Paper,
  Project,
  register,
  Reminder,
  ResearchDocument,
  searchPapers,
  searchLiterature,
  markPaperRecent,
  unmarkPaperRecent,
  LiteratureSearchResponse,
  ResearchAnalysis,
  FollowUp,
  snoozeFollowUp,
  uploadResearchDocument,
  UserProfile,
  summarizeDocuments,
  DocumentSummaryItem,
  deleteFollowUp,
  getDocumentContent,
} from '../../lib/api';

export default function WorkspacePage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  const [projects, setProjects] = useState<Project[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [searchResults, setSearchResults] = useState<Paper[] | null>(null);
  const [notifications, setNotifications] =
    useState<Notification[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');

  const [title, setTitle] = useState('');
  const [domain, setDomain] = useState('');

  const [paperTitle, setPaperTitle] = useState('');
  const [paperAbstract, setPaperAbstract] =
    useState('');
  const [paperQuery, setPaperQuery] = useState('');
  const [editingPaperId, setEditingPaperId] = useState<number | null>(null);
  const [editingPaperTitle, setEditingPaperTitle] = useState('');
  const [editingPaperAbstract, setEditingPaperAbstract] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [evidenceSuccess, setEvidenceSuccess] = useState('');
  const [evidenceError, setEvidenceError] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [workspaceDocuments, setWorkspaceDocuments] = useState<ResearchDocument[]>([]);
  const [uploadDocProjectId, setUploadDocProjectId] = useState<string>('');
  const [docFilterProjectId, setDocFilterProjectId] = useState<string>('all');
  const [viewingDocContentId, setViewingDocContentId] = useState<number | null>(null);
  const [docContentMap, setDocContentMap] = useState<Record<number, string>>({});
  const [loadingDocContentId, setLoadingDocContentId] = useState<number | null>(null);
  const [followUpFilterProjectId, setFollowUpFilterProjectId] = useState<string>('all');
  const [followUpCreateProjectId, setFollowUpCreateProjectId] = useState<string>('');

  const [isRegistering, setIsRegistering] =
    useState(false);
  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] = useState('');

  const [researchIdea, setResearchIdea] =
    useState('');

  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [reminderTitle, setReminderTitle] = useState('');
  const [reminderDescription, setReminderDescription] = useState('');
  const [reminderDatetime, setReminderDatetime] = useState('');
  const [reminderTimezone, setReminderTimezone] = useState('Asia/Kolkata');

  const [researchAnalysis, setResearchAnalysis] =
    useState<ResearchAnalysis | null>(null);

  const [isAnalyzing, setIsAnalyzing] =
    useState(false);

  // Document Summaries
  const [docSummaries, setDocSummaries] = useState<DocumentSummaryItem[] | null>(null);
  const [summarizingDocs, setSummarizingDocs] = useState(false);

  async function handleSummarizeWorkspaceDocuments() {
    if (!token) return;
    setSummarizingDocs(true);
    setError('');
    try {
      const res = await summarizeDocuments(token);
      setDocSummaries(res.summaries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to summarize documents.');
    } finally {
      setSummarizingDocs(false);
    }
  }

  // Literature Search (paginated)
  const [litQuery, setLitQuery] = useState('');
  const [litResults, setLitResults] = useState<LiteratureSearchResponse | null>(null);
  const [litSearching, setLitSearching] = useState(false);
  const [litPage, setLitPage] = useState(1);
  const [litPer_page] = useState(20);
  // Sorting for literature search
  const [litSort, setLitSort] = useState<'relevance' | 'citations' | 'year-desc' | 'year-asc'>('relevance');

  // Active section for tabs
  const [activeTab, setActiveTab] = useState<'projects' | 'evidence' | 'papers' | 'recent' | 'library'>('projects');

  const [connecting, setConnecting] =
    useState(false);

  const providersUnavailable =
    error.toLowerCase().includes('literature provider') ||
    error.toLowerCase().includes('external literature') ||
    error.toLowerCase().includes('semantic scholar') ||
    error.toLowerCase().includes('crossref');

  async function loadWorkspaceData(accessToken: string) {
    setConnecting(true);
    setError('');
    try {
      const [
        loadedProfile,
        loadedProjects,
        loadedPapers,
        loadedNotifications,
        loadedFollowUps,
        loadedReminders,
        loadedDocs,
      ] = await Promise.allSettled([
        getMe(accessToken),
        listProjects(accessToken),
        listPapers(accessToken),
        listNotifications(accessToken),
        listFollowUps(accessToken),
        listReminders(accessToken),
        listDocuments(accessToken, undefined, true),
      ]);
      if (loadedProfile.status === 'fulfilled') setUserProfile(loadedProfile.value);
      if (loadedProjects.status === 'fulfilled') setProjects(loadedProjects.value);
      if (loadedPapers.status === 'fulfilled') setPapers(loadedPapers.value);
      if (loadedNotifications.status === 'fulfilled') setNotifications(loadedNotifications.value);
      if (loadedFollowUps.status === 'fulfilled') setFollowUps(loadedFollowUps.value);
      if (loadedReminders.status === 'fulfilled') setReminders(loadedReminders.value);
      if (loadedDocs.status === 'fulfilled') setWorkspaceDocuments(loadedDocs.value);
      const firstFailure = [loadedProfile, loadedProjects, loadedPapers, loadedNotifications, loadedFollowUps, loadedReminders]
        .find((r): r is PromiseRejectedResult => r.status === 'rejected');
      if (firstFailure) {
        const msg = firstFailure.reason instanceof Error ? firstFailure.reason.message : '';
        if (msg === 'Invalid token' || msg === 'Authentication required') {
          window.localStorage.removeItem('access_token');
          setToken(null);
          setIsAuthChecking(false);
          router.replace('/login');
          return;
        }
        setError(msg || 'Unable to load workspace.');
      }
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load workspace.'
      );
    } finally {
      setConnecting(false);
    }
  }

  useEffect(() => {
    const savedToken =
      window.localStorage.getItem(
        'access_token'
      );

    if (!savedToken) {
      router.replace('/login');
      return;
    }

    setToken(savedToken);
    setIsAuthChecking(false);
    loadWorkspaceData(savedToken);
  }, [router]);

  useEffect(() => {
    if (!token) return;
    const interval = setInterval(async () => {
      try {
        const fresh = await listReminders(token);
        setReminders(fresh);
      } catch {
        // silent background poll failure
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [token]);

  async function handleAuth(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError('');
    setIsLoading(true);

    try {
      const response = isRegistering
        ? await register(
            email,
            password,
            name
          )
        : await login(
            email,
            password
          );

      window.localStorage.setItem(
        'access_token',
        response.access_token
      );

      setToken(response.access_token);
      await loadWorkspaceData(response.access_token);
    } catch (authError) {
      setError(
        authError instanceof Error
          ? authError.message
          : 'Authentication failed.'
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResearchAnalysis(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      !token ||
      researchIdea.trim().length < 5
    ) {
      return;
    }

    setError('');
    setIsAnalyzing(true);

    try {
      const result =
        await analyzeResearch(
          token,
          researchIdea.trim()
        );

      setResearchAnalysis(result);
    } catch (analysisError) {
      setError(
        analysisError instanceof Error
          ? analysisError.message
          : 'Research analysis failed.'
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleCreatePaper(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!token) return;

    const titleTrimmed = paperTitle.trim();
    if (!titleTrimmed) return;

    setEvidenceSuccess('');
    setEvidenceError('');

    if (papers.some((p) => p.title.trim().toLowerCase() === titleTrimmed.toLowerCase())) {
      setEvidenceError('An evidence item with this title already exists in your workspace.');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      const paper =
        await createPaper(
          token,
          titleTrimmed,
          paperAbstract.trim()
        );

      setPapers((current) => [
        paper,
        ...current,
      ]);

      setEvidenceSuccess(`Evidence "${paper.title}" saved successfully.`);
      setPaperTitle('');
      setPaperAbstract('');
      setTimeout(() => setEvidenceSuccess(''), 5000);
    } catch (paperError) {
      setEvidenceError(
        paperError instanceof Error
          ? paperError.message
          : 'Failed to save evidence.'
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeletePaper(paperId: number) {
    if (!token) return;
    try {
      await deletePaper(token, paperId);
      setPapers((current) => current.filter((p) => p.id !== paperId));
      setSearchResults((current) => current ? current.filter((p) => p.id !== paperId) : null);
      setDeleteConfirmId(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to delete evidence.'
      );
    }
  }

  async function handleUpdatePaper(paperId: number) {
    if (!token) return;
    try {
      const updated = await updatePaper(token, paperId, {
        title: editingPaperTitle,
        abstract: editingPaperAbstract,
      });
      setPapers((current) => current.map((p) => (p.id === paperId ? updated : p)));
      setEditingPaperId(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to update evidence.'
      );
    }
  }

  async function handleDocumentUpload() {
    if (!token || !selectedFile) return;
    setError('');
    setUploadStatus('Uploading and extracting text…');
    setUploading(true);
    try {
      const pid = uploadDocProjectId ? Number(uploadDocProjectId) : undefined;
      const doc = await uploadResearchDocument(token, selectedFile, undefined, pid);
      setUploadStatus(`Saved ${doc.filename} · ${doc.extracted_characters.toLocaleString()} characters extracted`);
      setWorkspaceDocuments((prev) => [doc, ...prev]);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (uploadError) {
      setUploadStatus('');
      setError(uploadError instanceof Error ? uploadError.message : 'Document upload failed.');
    } finally {
      setUploading(false);
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

  async function handleDeleteDocument(docId: number) {
    if (!token || !window.confirm('Delete this document? This cannot be undone.')) return;
    try {
      await deleteDocument(token, docId);
      setWorkspaceDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document.');
    }
  }

  async function updateFollowUp(action: 'complete' | 'snooze', followupId: number) {
    if (!token) return;
    try {
      const updated = action === 'complete'
        ? await completeFollowUp(token, followupId)
        : await snoozeFollowUp(token, followupId);
      setFollowUps((current) => current.map((followup) => followup.id === updated.id ? updated : followup));
    } catch (followupError) {
      setError(followupError instanceof Error ? followupError.message : 'Follow-up update failed.');
    }
  }

  async function handleDeleteFollowUp(followupId: number) {
    if (!token) return;
    try {
      await deleteFollowUp(token, followupId);
      setFollowUps((current) => current.filter((followup) => followup.id !== followupId));
    } catch (followupError) {
      setError(followupError instanceof Error ? followupError.message : 'Follow-up deletion failed.');
    }
  }

  async function handleCreateFollowUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const pidVal = form.get('project_id');
    const pid = pidVal && String(pidVal).trim() !== '' ? Number(pidVal) : undefined;
    try {
      const followup = await createFollowUp(
        token,
        String(form.get('title')),
        String(form.get('message')),
        pid
      );
      setFollowUps((current) => [...current, followup]);
      formElement?.reset();
      setFollowUpCreateProjectId('');
    } catch (followupError) {
      setError(followupError instanceof Error ? followupError.message : 'Follow-up creation failed.');
    }
  }

  async function handlePaperSearch(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      !token ||
      paperQuery.trim().length < 2
    ) {
      return;
    }

    setError('');

    try {
      const results = await searchPapers(
        token,
        paperQuery.trim()
      );
      setSearchResults(results);
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : 'Paper search failed.'
      );
    }
  }

  function clearPaperSearch() {
    setSearchResults(null);
    setPaperQuery('');
  }

  // Literature search with pagination
  async function handleLiteratureSearch(page: number = 1) {
    if (!token || litQuery.trim().length < 2) return;
    setLitSearching(true);
    setError('');
    try {
      const result = await searchLiterature(token, litQuery.trim(), page, litPer_page, 60);
      setLitResults(result);
      setLitPage(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Literature search failed.');
    } finally {
      setLitSearching(false);
    }
  }

  // Sort literature results client-side
  const sortedLitResults = litResults ? {
    ...litResults,
    results: [...litResults.results].sort((a, b) => {
      switch (litSort) {
        case 'citations': return (b.citation_count || 0) - (a.citation_count || 0);
        case 'year-desc': return (b.year || 0) - (a.year || 0);
        case 'year-asc': return (a.year || 9999) - (b.year || 9999);
        case 'relevance':
        default: return (b.relevance_score || 0) - (a.relevance_score || 0);
      }
    }),
  } : null;

  async function handleToggleRecent(paperId: number, isRecent: boolean) {
    if (!token) return;
    try {
      const updated = isRecent
        ? await unmarkPaperRecent(token, paperId)
        : await markPaperRecent(token, paperId);
      setPapers((prev) => prev.map((p) => (p.id === paperId ? updated : p)));
      if (searchResults) {
        setSearchResults((prev) => prev ? prev.map((p) => (p.id === paperId ? updated : p)) : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update paper.');
    }
  }

  async function handleCreateProject(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!token) return;

    setError('');
    setIsLoading(true);

    try {
      const project =
        await createProject(
          token,
          title,
          domain
        );

      setProjects((current) => [
        project,
        ...current,
      ]);

      setTitle('');
      setDomain('');

      // Navigate to the new project workspace
      window.location.href = `/workspace/${project.id}`;
    } catch (projectError) {
      setError(
        projectError instanceof Error
          ? projectError.message
          : 'Project creation failed.'
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleMarkRead(
    notificationId: number
  ) {
    if (!token) return;

    try {
      const updated =
        await markNotificationRead(
          token,
          notificationId
        );

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === updated.id
            ? updated
            : notification
        )
      );
    } catch (notificationError) {
      setError(
        notificationError instanceof Error
          ? notificationError.message
          : 'Notification update failed.'
      );
    }
  }

  async function handleCreateReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError('');
    try {
      const reminder = await createReminder(
        token,
        reminderTitle,
        reminderDescription || null,
        reminderDatetime,
        reminderTimezone || 'Asia/Kolkata'
      );
      setReminders((current) => [...current, reminder]);
      setReminderTitle('');
      setReminderDescription('');
      setReminderDatetime('');
    } catch (reminderError) {
      setError(reminderError instanceof Error ? reminderError.message : 'Reminder creation failed.');
    }
  }

  async function handleCancelReminder(reminderId: number) {
    if (!token) return;
    try {
      const updated = await cancelReminder(token, reminderId);
      setReminders((current) => current.map((r) => r.id === updated.id ? updated : r));
    } catch (reminderError) {
      setError(reminderError instanceof Error ? reminderError.message : 'Failed to cancel reminder.');
    }
  }

  async function handleCompleteReminder(reminderId: number) {
    if (!token) return;
    try {
      const updated = await completeReminder(token, reminderId);
      setReminders((current) => current.map((r) => r.id === updated.id ? updated : r));
    } catch (reminderError) {
      setError(reminderError instanceof Error ? reminderError.message : 'Failed to complete reminder.');
    }
  }

  async function handleDeleteReminder(reminderId: number) {
    if (!token) return;
    try {
      await deleteReminder(token, reminderId);
      setReminders((current) => current.filter((r) => r.id !== reminderId));
    } catch (reminderError) {
      setError(reminderError instanceof Error ? reminderError.message : 'Failed to delete reminder.');
    }
  }

  function formatReminderDate(dt: string, tz?: string) {
    const targetTz = tz || 'Asia/Kolkata';
    try {
      const date = new Date(dt);
      if (isNaN(date.getTime())) return dt;

      // Extract calendar day in target timezone
      const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: targetTz,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });
      const now = new Date();
      const targetDayStr = formatter.format(date);
      const todayDayStr = formatter.format(now);

      const [tY, tM, tD] = targetDayStr.split('-').map(Number);
      const [nY, nM, nD] = todayDayStr.split('-').map(Number);
      const targetCal = new Date(tY, tM - 1, tD).getTime();
      const todayCal = new Date(nY, nM - 1, nD).getTime();
      const dayDiff = Math.round((targetCal - todayCal) / 86400000);

      const timeStr = date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: targetTz,
      });

      if (dayDiff === 0) {
        return `Today at ${timeStr}`;
      } else if (dayDiff === 1) {
        return `Tomorrow at ${timeStr}`;
      } else if (dayDiff === -1) {
        return `Yesterday at ${timeStr}`;
      } else {
        const dateStr = date.toLocaleDateString([], {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          timeZone: targetTz,
        });
        return `${dateStr} at ${timeStr}`;
      }
    } catch {
      return dt;
    }
  }

  function signOut() {
    window.localStorage.removeItem(
      'access_token'
    );

    setToken(null);
    setUserProfile(null);
    setProjects([]);
    setPapers([]);
    setNotifications([]);
    setFollowUps([]);
    setReminders([]);
    setResearchAnalysis(null);
    setWorkspaceDocuments([]);
    router.replace('/login');
  }

  if (isAuthChecking || !token) {
    return (
      <main className="research-shell workspace-page min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="research-processing-orb mx-auto" />
          <p className="mt-4 text-sm font-medium uppercase tracking-widest text-cyan-400">ResearchOS</p>
          <p className="mt-2 text-sm text-slate-400">Loading workspace…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="research-shell workspace-page min-h-screen bg-slate-950 p-6 text-slate-50 sm:p-10">
      <div className="mx-auto max-w-7xl">

        {/* HEADER */}

        <header className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="workspace-brand">
            <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              ResearchOS
            </p>

            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              AI-Powered Research Intelligence
            </h1>

            <p className="workspace-kicker">Research workspace</p>

            <p className="mt-3 max-w-3xl text-slate-400">
              Transform your research ideas into evidence-backed insights and a clear roadmap to success.
            </p>
            </div>
          </div>

          <div className="workspace-header-actions">
            <nav aria-label="Workspace navigation" className="workspace-nav"><a href="/workspace">Workspace</a><a href="/dashboard">Projects</a><a href="/research/new">Research Ideas</a><a href="/workspace#evidence">Evidence</a><a href="/workspace#followups">Follow-ups</a><a href="/workspace#reminders">Reminders</a></nav>
            <div className="flex items-center gap-3">
              <ConnectionStatus />
              {token && (
                <>
                  {userProfile && <span className="text-sm text-slate-500">{userProfile.name}</span>}
                  <button
                    onClick={signOut}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-cyan-400 hover:text-white"
                  >
                    Sign out
                  </button>
                </>
              )}
            </div>
          </div>
        </header>

        {/* ERROR */}

        {error && providersUnavailable ? (
          <div
            role="status"
            className="mt-6 flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900"
          >
            <span>External literature providers are currently unavailable. Local ResearchOS features remain available.</span>
          </div>
        ) : error && (
          <div
            role="alert"
            className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50/90 px-4 py-3 text-sm text-rose-900"
          >
            <span>
              {error.toLowerCase().includes('unavailable') || error.toLowerCase().includes('failed to fetch') || error.toLowerCase().includes('could not connect')
                ? 'Research server is currently unavailable.'
                : error}
            </span>
            <button
              type="button"
              onClick={() => token && loadWorkspaceData(token)}
              className="rounded-lg border border-rose-300 bg-white px-3 py-1.5 font-medium text-rose-700 shadow-sm transition hover:bg-rose-100"
            >
              Retry Connection
            </button>
          </div>
        )}

        <aside className="workspace-sidebar" aria-label="ResearchOS navigation">
          <div className="workspace-sidebar-brand"><div><strong>ResearchOS</strong><small>AI Research Intelligence</small></div></div>
          <nav>
            <a className="active" href="/workspace"><i aria-hidden="true">◈</i>Workspace</a>
            <a href="/dashboard"><i aria-hidden="true">▦</i>Projects</a>
            <a href="/research/new"><i aria-hidden="true">✦</i>Research Ideas</a>
            <span><i aria-hidden="true">⌕</i>Literature</span><span><i aria-hidden="true">◌</i>Experiments</span><span><i aria-hidden="true">↗</i>Roadmap</span><span><i aria-hidden="true">▤</i>Datasets</span><span><i aria-hidden="true">◫</i>Analytics</span><span><i aria-hidden="true">⏰</i>Reminders</span>
          </nav>
          {userProfile && <p>Signed in as {userProfile.name}</p>}
        </aside>

        {connecting ? (
          <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 p-10 text-center">
            <p className="text-sm font-medium uppercase tracking-widest text-cyan-400">ResearchOS</p>
            <h2 className="mt-3 text-xl font-semibold">Connecting to research engine...</h2>
            <p className="mt-2 text-sm text-slate-400">Please wait while the workspace loads.</p>
          </div>
        ) : (
          <>
            {/* PROJECTS */}

            <section className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">

              <div>
                <div className="flex items-end justify-between gap-4">

                  <div>
                    <p className="text-sm text-slate-500">
                      Your research portfolio
                    </p>

                    <h2 className="mt-1 text-2xl font-semibold">
                      Projects
                    </h2>
                  </div>

                  <span className="text-sm text-slate-500">
                    {projects.length} active
                  </span>
                </div>

                <div className="mt-5 space-y-3">

                  {projects.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center text-slate-400">
                      Your first research project starts here.
                    </div>
                  ) : (
                    projects.map((project) => (
                      <article
                        key={project.id}
                        className="rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-cyan-500/40 cursor-pointer"
                        onClick={() => window.location.href = `/workspace/${project.id}`}
                      >
                        <div className="flex items-start justify-between gap-4">

                          <div>
                            <h3 className="font-semibold">
                              {project.title}
                            </h3>

                            <p className="mt-1 text-sm text-slate-400">
                              {project.domain}
                            </p>
                          </div>

                          <span className="rounded-full bg-emerald-950 px-3 py-1 text-xs text-emerald-300">
                            {project.status}
                          </span>
                        </div>

                        <div className="mt-4 flex items-center justify-between">
                          <span className="text-xs text-slate-500">Project #{project.id}</span>
                          <span className="text-sm font-medium text-cyan-400">Open workspace →</span>
                        </div>
                      </article>
                    ))
                  )}

                </div>
              </div>

              <form
                onSubmit={handleCreateProject}
                className="h-fit rounded-xl border border-slate-800 bg-slate-900 p-5"
              >
                <h2 className="font-semibold">
                  Start a project
                </h2>

                <p className="mt-2 text-sm text-slate-400">
                  Give your next research question a home.
                </p>

                <div className="mt-5 space-y-3">

                  <input
                    required
                    minLength={3}
                    value={title}
                    onChange={(event) =>
                      setTitle(event.target.value)
                    }
                    placeholder="Project title"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400"
                  />

                  <input
                    required
                    minLength={2}
                    value={domain}
                    onChange={(event) =>
                      setDomain(event.target.value)
                    }
                    placeholder="Research domain"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400"
                  />

                  <button
                    disabled={isLoading}
                    className="w-full rounded-lg bg-white px-4 py-3 font-semibold text-slate-950 disabled:opacity-50"
                  >
                    Create project
                  </button>

                </div>
              </form>

              <ol className="research-stepper" aria-label="Research pipeline">
                {['Literature Search', 'Paper Analysis', 'Gap Analysis', 'Dataset Recommendation', 'Experiment Planning', 'Research Roadmap'].map((stage, index) => (
                  <li key={stage}><span>{index + 1}</span>{stage}</li>
                ))}
              </ol>
            </section>

            {/* PAPERS */}

            <section className="mt-10 border-t border-slate-800 pt-8">

              <div className="flex flex-wrap items-end justify-between gap-4">

                <div>
                  <p className="text-sm text-slate-500">
                    Evidence library
                  </p>

                  <h2 className="mt-1 text-2xl font-semibold">
                    Papers
                  </h2>
                </div>

                <form
                  onSubmit={handlePaperSearch}
                  className="flex gap-2"
                >
                  <input
                    value={paperQuery}
                    onChange={(event) =>
                      setPaperQuery(
                        event.target.value
                      )
                    }
                    placeholder="Search your papers"
                    className="w-56 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-cyan-400"
                  />

                  <button className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:border-cyan-400">
                    Search
                  </button>
                </form>

              </div>

              <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">

                <div className="space-y-3">

                  {searchResults !== null && (
                    <div className="flex items-center justify-between rounded-xl border border-cyan-800 bg-cyan-950/30 px-4 py-2">
                      <span className="text-xs text-cyan-300">
                        Showing search results ({searchResults.length} found)
                      </span>
                      <button
                        onClick={clearPaperSearch}
                        className="text-xs text-cyan-400 hover:text-cyan-200"
                      >
                        Clear search & show all
                      </button>
                    </div>
                  )}

                  {(searchResults !== null ? searchResults : papers).length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-700 px-6 py-10 text-center text-slate-400">
                      {searchResults !== null ? 'No matching evidence found.' : 'No evidence records yet.'}
                    </div>
                  ) : (
                    (searchResults !== null ? searchResults : papers).map((paper) => (
                      <article
                        key={paper.id}
                        className="rounded-xl border border-slate-800 bg-slate-900 p-5"
                      >
                        {editingPaperId === paper.id ? (
                          /* ── Edit mode ── */
                          <div className="space-y-3">
                            <input
                              value={editingPaperTitle}
                              onChange={(e) => setEditingPaperTitle(e.target.value)}
                              className="w-full rounded-lg border border-cyan-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                              placeholder="Paper title"
                            />
                            <textarea
                              value={editingPaperAbstract}
                              onChange={(e) => setEditingPaperAbstract(e.target.value)}
                              rows={4}
                              className="w-full resize-none rounded-lg border border-cyan-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                              placeholder="Abstract or evidence notes"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleUpdatePaper(paper.id)}
                                disabled={!editingPaperTitle.trim()}
                                className="rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 disabled:opacity-50"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => setEditingPaperId(null)}
                                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* ── View mode ── */
                          <>
                            <div className="flex items-start justify-between gap-3">
                              <h3 className="font-semibold">
                                {paper.title}
                              </h3>
                              <div className="flex shrink-0 gap-1">
                                <button
                                  onClick={() => {
                                    setEditingPaperId(paper.id);
                                    setEditingPaperTitle(paper.title);
                                    setEditingPaperAbstract(paper.abstract || '');
                                  }}
                                  className="rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-cyan-500 hover:text-cyan-300"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => setDeleteConfirmId(paper.id)}
                                  className="rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-rose-500 hover:text-rose-400"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>

                            <p className="mt-2 text-sm leading-6 text-slate-400">
                              {paper.abstract ||
                                'No abstract provided.'}
                            </p>

                            <p className="mt-3 text-xs uppercase tracking-wider text-cyan-400">
                              {paper.evidence_level} evidence
                            </p>

                            {/* Delete confirmation */}
                            {deleteConfirmId === paper.id && (
                              <div className="mt-3 rounded-lg border border-rose-800 bg-rose-950/40 p-3">
                                <p className="text-xs text-rose-300">Delete this evidence record? This cannot be undone.</p>
                                <div className="mt-2 flex gap-2">
                                  <button
                                    onClick={() => handleDeletePaper(paper.id)}
                                    className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-500"
                                  >
                                    Confirm Delete
                                  </button>
                                  <button
                                    onClick={() => setDeleteConfirmId(null)}
                                    className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:text-slate-200"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </article>
                    ))
                  )}

                </div>

                <form
                  onSubmit={handleCreatePaper}
                  className="h-fit rounded-xl border border-slate-800 bg-slate-900 p-5"
                >
                  <h2 className="font-semibold">
                    Add evidence
                  </h2>

                  <div className="mt-5 space-y-3">

                    <input
                      required
                      minLength={3}
                      value={paperTitle}
                      onChange={(event) => {
                        setPaperTitle(event.target.value);
                        if (evidenceError) setEvidenceError('');
                      }}
                      placeholder="Paper title"
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400"
                    />

                    <textarea
                      required
                      value={paperAbstract}
                      onChange={(event) =>
                        setPaperAbstract(
                          event.target.value
                        )
                      }
                      placeholder="Abstract or evidence notes"
                      rows={5}
                      className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400"
                    />

                    <button
                      type="submit"
                      disabled={isLoading || !paperTitle.trim()}
                      className="w-full rounded-lg bg-white px-4 py-3 font-semibold text-slate-950 disabled:opacity-50 transition hover:bg-slate-100"
                    >
                      {isLoading ? 'Saving evidence…' : 'Save Evidence'}
                    </button>

                    {evidenceSuccess && (
                      <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">
                        ✓ {evidenceSuccess}
                      </p>
                    )}

                    {evidenceError && (
                      <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
                        ⚠ {evidenceError}
                      </p>
                    )}

                  </div>
                </form>

                <form
                  onSubmit={(e) => { e.preventDefault(); handleDocumentUpload(); }}
                  className="h-fit rounded-xl border border-dashed border-cyan-900 bg-slate-900 p-5"
                >
                  <h2 className="font-semibold">Upload Supporting Document</h2>
                  <p className="mt-2 text-sm text-slate-400">
                    PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, HTML, JSON, XML, PNG, JPG
                  </p>
                  <label className="mt-4 block text-xs text-slate-400">
                    Associate with Project (optional):
                  </label>
                  <select
                    value={uploadDocProjectId}
                    onChange={(e) => setUploadDocProjectId(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-cyan-400"
                  >
                    <option value="">General Workspace (No project)</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        Project #{p.id} — {p.title}
                      </option>
                    ))}
                  </select>
                  <input
                    ref={fileInputRef}
                    type="file"
                    required
                    accept=".txt,.md,.markdown,.pdf,.docx,.csv,.xlsx,.xls,.pptx,.doc,.html,.htm,.json,.xml,.png,.jpg,.jpeg,.webp"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                    className="mt-4 block w-full text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-2 file:text-slate-200"
                  />
                  {selectedFile && (
                    <p className="mt-2 text-xs text-slate-500">Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</p>
                  )}
                  <button
                    type="submit"
                    disabled={!selectedFile || uploading}
                    className="mt-4 w-full rounded-lg border border-cyan-700 px-4 py-3 text-sm font-semibold text-cyan-300 hover:bg-cyan-950 disabled:opacity-50"
                  >
                    {uploading ? 'Uploading…' : 'Upload Document'}
                  </button>
                  {uploadStatus && <p className="mt-3 text-xs text-emerald-300">{uploadStatus}</p>}
                </form>

              </div>
            </section>

            <section id="followups" className="mt-10 border-t border-slate-800 pt-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-violet-400">Research continuity</p>
                  <h2 className="mt-1 text-2xl font-semibold">Follow-ups</h2>
                </div>
                <div className="flex items-center gap-3">
                  <select
                    value={followUpFilterProjectId}
                    onChange={(e) => setFollowUpFilterProjectId(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-cyan-400"
                  >
                    <option value="all">All Follow-ups ({followUps.length})</option>
                    <option value="general">General (No project)</option>
                    {projects.map((p) => (
                      <option key={p.id} value={String(p.id)}>
                        Project #{p.id} — {p.title}
                      </option>
                    ))}
                  </select>
                  <span className="text-sm text-slate-500">
                    {followUps.filter((followup) => followup.status === 'pending').length} pending
                  </span>
                </div>
              </div>
              <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-3">
                  {followUps.filter((f) => {
                    if (followUpFilterProjectId === 'all') return true;
                    if (followUpFilterProjectId === 'general') return !f.project_id;
                    return f.project_id === Number(followUpFilterProjectId);
                  }).length === 0 ? (
                    <p className="rounded-xl border border-dashed border-slate-700 px-6 py-8 text-center text-slate-400">
                      No research follow-ups match this filter.
                    </p>
                  ) : (
                    followUps
                      .filter((f) => {
                        if (followUpFilterProjectId === 'all') return true;
                        if (followUpFilterProjectId === 'general') return !f.project_id;
                        return f.project_id === Number(followUpFilterProjectId);
                      })
                      .map((followup) => {
                        const assocProject = followup.project_id
                          ? projects.find((p) => p.id === followup.project_id)
                          : null;
                        return (
                          <article key={followup.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-slate-700">
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <h3 className="font-semibold text-slate-100">{followup.title}</h3>
                                <p className="mt-2 text-sm text-slate-400">{followup.message}</p>
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                  {assocProject ? (
                                    <span className="rounded-full bg-cyan-950 px-2.5 py-0.5 text-xs text-cyan-300">
                                      Project #{assocProject.id}: {assocProject.title}
                                    </span>
                                  ) : (
                                    <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-400">
                                      General Workspace
                                    </span>
                                  )}
                                  <span className="text-xs text-slate-500">
                                    Created {new Date(followup.created_at).toLocaleDateString()}
                                  </span>
                                </div>
                              </div>
                              <span
                                className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
                                  followup.status === 'completed'
                                    ? 'bg-emerald-950 text-emerald-300'
                                    : followup.status === 'snoozed'
                                    ? 'bg-amber-950 text-amber-300'
                                    : 'bg-violet-950 text-violet-300'
                                }`}
                              >
                                {followup.status}
                              </span>
                            </div>
                            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
                              <div className="flex gap-2">
                                {followup.status !== 'completed' && (
                                  <button
                                    onClick={() => updateFollowUp('complete', followup.id)}
                                    className="rounded-lg bg-cyan-400 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                                  >
                                    ✓ Complete
                                  </button>
                                )}
                                {followup.status !== 'completed' && (
                                  <button
                                    onClick={() => updateFollowUp('snooze', followup.id)}
                                    className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-600 transition"
                                  >
                                    Snooze 24h
                                  </button>
                                )}
                              </div>
                              <button
                                onClick={() => handleDeleteFollowUp(followup.id)}
                                className="rounded-lg border border-slate-800 px-2.5 py-1.5 text-xs text-slate-400 hover:border-rose-800 hover:text-rose-400 transition"
                                title="Delete follow-up"
                              >
                                Delete
                              </button>
                            </div>
                          </article>
                        );
                      })
                  )}
                </div>
                <form onSubmit={handleCreateFollowUp} className="h-fit rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <h2 className="font-semibold">Add a follow-up</h2>
                  <div className="mt-4 space-y-3">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">
                        Associate with Project (optional):
                      </label>
                      <select
                        name="project_id"
                        value={followUpCreateProjectId}
                        onChange={(e) => setFollowUpCreateProjectId(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-cyan-400"
                      >
                        <option value="">General (No project)</option>
                        {projects.map((p) => (
                          <option key={p.id} value={p.id}>
                            Project #{p.id} — {p.title}
                          </option>
                        ))}
                      </select>
                    </div>
                    <input
                      name="title"
                      required
                      minLength={3}
                      placeholder="Next research action"
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400 text-slate-100 placeholder:text-slate-500"
                    />
                    <textarea
                      name="message"
                      required
                      minLength={3}
                      placeholder="What should happen next?"
                      rows={4}
                      className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400 text-slate-100 placeholder:text-slate-500"
                    />
                    <button className="w-full rounded-lg bg-white px-4 py-3 font-semibold text-slate-950 hover:bg-slate-200 transition">
                      Create follow-up
                    </button>
                  </div>
                </form>
              </div>
            </section>

            {/* SUPPORTING DOCUMENTS / EVIDENCE LIBRARY */}

            <section id="evidence" className="mt-10 border-t border-slate-800 pt-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-cyan-400">Evidence Library</p>
                  <h2 className="mt-1 text-2xl font-semibold">Supporting Documents</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Upload research papers, datasets, and documents for AI-powered analysis.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <select
                    value={docFilterProjectId}
                    onChange={(e) => setDocFilterProjectId(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-cyan-400"
                  >
                    <option value="all">All Documents ({workspaceDocuments.length})</option>
                    <option value="workspace">General Workspace</option>
                    {projects.map((p) => (
                      <option key={p.id} value={String(p.id)}>
                        Project #{p.id} — {p.title}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleSummarizeWorkspaceDocuments}
                    disabled={summarizingDocs || workspaceDocuments.length === 0}
                    className="rounded-lg bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50"
                  >
                    {summarizingDocs ? 'Summarizing…' : `Summarize Documents (${workspaceDocuments.length})`}
                  </button>
                </div>
              </div>

              {summarizingDocs && (
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-cyan-900/60 bg-slate-900/80 p-4">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                  <p className="text-sm text-slate-300">Summarizing workspace documents with grounded AI analysis…</p>
                </div>
              )}

              {docSummaries && !summarizingDocs && (
                <div className="mt-4 space-y-3 rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-slate-100">
                      📄 Document Summaries ({docSummaries.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() => setDocSummaries(null)}
                      className="text-xs text-slate-400 hover:text-slate-200"
                    >
                      Clear summaries
                    </button>
                  </div>
                  {docSummaries.length === 0 ? (
                    <p className="text-xs text-slate-400">No documents in workspace to summarize.</p>
                  ) : (
                    docSummaries.map((ds) => (
                      <article key={ds.document_id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h4 className="font-semibold text-sm text-cyan-300">{ds.title}</h4>
                            <p className="mt-0.5 text-xs text-slate-500">{ds.filename} · {ds.extracted_characters.toLocaleString()} characters extracted</p>
                          </div>
                          <span className="shrink-0 rounded-full bg-cyan-950 px-2.5 py-0.5 text-xs text-cyan-300">Workspace Document</span>
                        </div>
                        {ds.summary && (
                          <div className="mt-3">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Summary</p>
                            <p className="mt-1 text-xs leading-relaxed text-slate-300">{ds.summary}</p>
                          </div>
                        )}
                        {ds.key_findings && ds.key_findings.length > 0 && (
                          <div className="mt-3">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Key Findings</p>
                            <ul className="mt-1 space-y-1">
                              {ds.key_findings.map((f, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                  <span className="mt-0.5 text-cyan-400">•</span>
                                  <span>{f}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {ds.methodology && ds.methodology.length > 0 && (
                          <div className="mt-3">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Methodology</p>
                            <div className="mt-1.5 flex flex-wrap gap-1.5">
                              {ds.methodology.map((m, i) => (
                                <span key={i} className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-300">
                                  {m}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </article>
                    ))
                  )}
                </div>
              )}

              <div className="mt-5 space-y-3">
                {workspaceDocuments.filter((doc) => {
                  if (docFilterProjectId === 'all') return true;
                  if (docFilterProjectId === 'workspace') return !doc.project_id;
                  return doc.project_id === Number(docFilterProjectId);
                }).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 px-6 py-10 text-center text-slate-400">
                    No supporting documents match this filter. Upload a document above.
                  </div>
                ) : (
                  workspaceDocuments
                    .filter((doc) => {
                      if (docFilterProjectId === 'all') return true;
                      if (docFilterProjectId === 'workspace') return !doc.project_id;
                      return doc.project_id === Number(docFilterProjectId);
                    })
                    .map((doc) => {
                      const assocProject = doc.project_id ? projects.find((p) => p.id === doc.project_id) : null;
                      return (
                        <article
                          key={doc.id}
                          className="rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-cyan-500/40"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold truncate text-slate-100">{doc.filename}</p>
                              <p className="mt-1 text-xs text-slate-500">
                                {doc.extracted_characters.toLocaleString()} characters extracted · {doc.content_type}
                                {assocProject ? ` · Project #${assocProject.id}: ${assocProject.title}` : doc.project_id ? ` · Project #${doc.project_id}` : ' · General Workspace'}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleViewDocumentContent(doc.id)}
                                className="shrink-0 rounded-lg border border-cyan-800 bg-cyan-950/40 px-2.5 py-1 text-xs font-medium text-cyan-300 hover:bg-cyan-900/60 transition"
                              >
                                {loadingDocContentId === doc.id
                                  ? 'Loading…'
                                  : viewingDocContentId === doc.id
                                  ? 'Hide Text'
                                  : 'View Extracted Text'}
                              </button>
                              <span className="shrink-0 rounded-full bg-emerald-950 px-2.5 py-1 text-xs text-emerald-300">✓ Ready</span>
                              <button
                                onClick={() => handleDeleteDocument(doc.id)}
                                className="shrink-0 rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-400 transition hover:border-rose-500 hover:text-rose-400"
                                title="Delete document"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                          {viewingDocContentId === doc.id && (
                            <div className="mt-3 border-t border-slate-800 pt-3">
                              <div className="flex items-center justify-between pb-1.5">
                                <span className="text-xs font-semibold text-cyan-400">
                                  Extracted Content Preview ({doc.extracted_characters.toLocaleString()} chars)
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setViewingDocContentId(null)}
                                  className="text-xs text-slate-400 hover:text-slate-200"
                                >
                                  Close Preview
                                </button>
                              </div>
                              <div className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-300">
                                {docContentMap[doc.id] || 'No extracted text found in document.'}
                              </div>
                            </div>
                          )}
                        </article>
                      );
                    })
                )}
              </div>
            </section>

            {/* AI RESEARCH INTELLIGENCE */}

            <section className="research-analysis-command mt-10 border-t border-slate-800 pt-8">

                <div>
                  <p className="text-sm text-cyan-400">
                    AI Research Intelligence
                  </p>

                  <h2 className="mt-1 text-2xl font-semibold">
                  What research problem or idea would you like to explore?
                  </h2>

                <p className="mt-2 max-w-3xl text-sm text-slate-400">
                  Describe a complete research problem, idea, or research question —
                  ResearchOS will run the full research-intelligence workflow:
                  literature retrieval, paper analysis, research-gap discovery,
                  dataset recommendations, experiment planning, and a research roadmap.
                </p>
              </div>

              <form
                onSubmit={handleResearchAnalysis}
                className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >

                <textarea
                  required
                  minLength={5}
                  value={researchIdea}
                  onChange={(event) =>
                    setResearchIdea(
                      event.target.value
                    )
                  }
                  placeholder="Describe your research problem, idea, or research question... e.g., AI-powered intrusion detection system for IoT networks"
                  rows={4}
                  className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none focus:border-cyan-400"
                />

                <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={isAnalyzing}
                  className="rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 disabled:opacity-50"
                >
                  {isAnalyzing
                    ? 'Analyzing research...'
                    : 'Analyze Research Idea'}
                </button>
                {researchIdea.trim().length >= 5 && (
                  <button
                    type="button"
                    onClick={() => {
                      setLitQuery(researchIdea.trim());
                      window.scrollTo({ top: document.querySelector('.mt-10.border-t.border-slate-800.pt-8')?.getBoundingClientRect()?.top ? window.scrollY + document.querySelector('.mt-10.border-t.border-slate-800.pt-8')!.getBoundingClientRect().top - 20 : window.scrollY, behavior: 'smooth' });
                    }}
                    className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-300 transition hover:border-cyan-400 hover:text-cyan-300"
                  >
                    Use in Literature Search ↓
                  </button>
                )}
                </div>

              </form>

              {isAnalyzing && (
                <div
                  role="status"
                  aria-live="polite"
                  className="research-processing mt-5 rounded-2xl border border-cyan-900/60 bg-slate-900/80 p-5"
                >
                  <div className="flex items-center gap-3">
                    <span className="research-processing-orb" aria-hidden="true" />
                    <div>
                      <p className="font-semibold text-slate-100">ResearchOS is analyzing your research question</p>
                      <p className="mt-1 text-sm text-slate-400">Live evidence is being retrieved and passed into the research workflow.</p>
                    </div>
                  </div>
                  <ol className="mt-5 grid gap-2 text-sm text-slate-300 sm:grid-cols-2 lg:grid-cols-3">
                    {['Literature Search', 'Paper Analysis', 'Gap Discovery', 'Dataset Recommendation', 'Experiment Planning', 'Roadmap Generation'].map((stage, index) => (
                      <li key={stage} className="research-processing-stage"><span>{index === 0 ? '●' : '○'}</span>{stage}</li>
                    ))}
                  </ol>
                </div>
              )}
            </section>

            {/* AI RESULTS */}

            {researchAnalysis && (
              <section className="research-results mt-8 space-y-6">

                {/* RESEARCH PROBLEM & OBJECTIVES */}

                <div className="rounded-2xl border border-cyan-900/50 bg-slate-900 p-6">

                  <p className="text-sm text-cyan-400">
                    Research Problem Formulation
                  </p>

                  <h3 className="mt-2 text-2xl font-semibold">
                    {researchAnalysis.plan.idea}
                  </h3>

                  {researchAnalysis.plan.problem_understanding && (
                    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                        Problem Understanding
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-300">
                        {researchAnalysis.plan.problem_understanding}
                      </p>
                    </div>
                  )}

                  <div className="mt-5">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Research Objectives
                    </p>
                    <div className="grid gap-3 md:grid-cols-3">
                      {researchAnalysis.plan.objectives.map(
                        (objective, index) => (
                          <div
                            key={index}
                            className="rounded-xl border border-slate-800 bg-slate-950 p-4"
                          >
                            <p className="text-xs text-cyan-400">
                              OBJECTIVE {index + 1}
                            </p>
                            <p className="mt-2 text-sm text-slate-300">
                              {objective}
                            </p>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {researchAnalysis.plan.research_questions && researchAnalysis.plan.research_questions.length > 0 && (
                    <div className="mt-5">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Core Research Questions
                      </p>
                      <div className="space-y-2">
                        {researchAnalysis.plan.research_questions.map((rq, index) => (
                          <div key={index} className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
                            <span className="shrink-0 rounded-full bg-cyan-950 px-2.5 py-0.5 text-xs font-bold text-cyan-400">
                              RQ{index + 1}
                            </span>
                            <span>{rq}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>

                <div className="research-overview" aria-label="Research overview">
                  <div>
                    <span>Analysis</span>
                    <strong>
                      {docFilterProjectId !== 'all' && docFilterProjectId !== 'workspace'
                        ? workspaceDocuments.filter((d) => d.project_id === Number(docFilterProjectId)).length
                        : (workspaceDocuments.length > 0 ? workspaceDocuments.length : (researchAnalysis.analysis.papers_processed || 0))}
                    </strong>
                    <small>Sources evaluated</small>
                  </div>
                  <div><span>Research gaps</span><strong>{researchAnalysis.research_gaps.gaps.length}</strong><small>Gaps found</small></div>
                  <div><span>Datasets</span><strong>{researchAnalysis.datasets.recommendations.length}</strong><small>Recommendations</small></div>
                  <div><span>Models</span><strong>{researchAnalysis.plan.model_recommendations?.length || 3}</strong><small>Architectures</small></div>
                  <div><span>Experiments</span><strong>{researchAnalysis.experiments.experiments.length}</strong><small>Planned</small></div>
                  <div><span>Roadmap</span><strong>{researchAnalysis.roadmap.milestones.length}</strong><small>Milestones</small></div>
                </div>

                {/* MODEL & ALGORITHM RECOMMENDATIONS */}

                {researchAnalysis.plan.model_recommendations && researchAnalysis.plan.model_recommendations.length > 0 && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm text-cyan-400">
                          Architecture Recommendations
                        </p>
                        <h3 className="mt-1 text-2xl font-semibold">
                          Recommended Models &amp; Algorithms
                        </h3>
                      </div>
                      <span className="rounded-full bg-cyan-950 px-3 py-1 text-xs text-cyan-300">
                        {researchAnalysis.plan.model_recommendations.length} Architectures
                      </span>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-3">
                      {researchAnalysis.plan.model_recommendations.map((model, idx) => (
                        <div key={idx} className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950 p-5">
                          <div>
                            <span className="rounded-full bg-cyan-950/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-400">
                              Candidate {idx + 1}
                            </span>
                            <h4 className="mt-2 font-semibold text-slate-100">
                              {model.name}
                            </h4>
                            <p className="mt-2 text-xs leading-relaxed text-slate-400">
                              {model.rationale}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* METHODOLOGY & ANALYSIS */}

                <div className="grid gap-6 lg:grid-cols-2">

                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-cyan-400">
                      Methodology Recommendations
                    </p>

                    <h3 className="mt-1 text-xl font-semibold">
                      Pipeline Stages &amp; Approaches
                    </h3>

                    {researchAnalysis.plan.methodology_recommendations && researchAnalysis.plan.methodology_recommendations.length > 0 ? (
                      <div className="mt-5 space-y-3">
                        {researchAnalysis.plan.methodology_recommendations.map((m, idx) => (
                          <div
                            key={idx}
                            className="rounded-lg border border-slate-800 bg-slate-950 p-3"
                          >
                            <p className="text-xs font-semibold text-cyan-400">
                              {m.stage}
                            </p>
                            <p className="mt-1 text-xs text-slate-300">
                              {m.details}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-5 space-y-3">
                        {Object.entries(
                          researchAnalysis.analysis
                            .method_distribution
                        ).map(
                          ([method, count]) => (
                            <div
                              key={method}
                              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-3"
                            >
                              <span className="text-sm text-slate-300">
                                {method}
                              </span>
                              <span className="rounded-full bg-cyan-950 px-3 py-1 text-xs text-cyan-300">
                                {count}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-cyan-400">
                      Key Findings
                    </p>

                    <h3 className="mt-1 text-xl font-semibold">
                      Analysis Summary
                    </h3>

                    <p className="mt-4 text-sm leading-6 text-slate-400">
                      {researchAnalysis.analysis.summary}
                    </p>

                    <div className="mt-5 space-y-2">

                      {researchAnalysis.analysis.key_findings.map(
                        (finding, index) => (
                          <div
                            key={index}
                            className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300"
                          >
                            • {finding}
                          </div>
                        )
                      )}

                    </div>
                  </div>

                </div>

                {/* RESEARCH GAPS */}

                <div className="rounded-2xl border border-amber-900/40 bg-slate-900 p-6">

                  <p className="text-sm text-amber-400">
                    Research Intelligence
                  </p>

                  <h3 className="mt-1 text-2xl font-semibold">
                    Identified Research Gaps
                  </h3>

                  <p className="mt-2 text-sm text-slate-400">
                    {researchAnalysis.research_gaps.papers_compared}{' '}
                    papers compared.
                  </p>

                  <div className="mt-5 grid gap-4 md:grid-cols-2">

                    {researchAnalysis.research_gaps.gaps.map(
                      (gap, index) => (
                        <article
                          key={index}
                          className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                        >

                          <div className="flex items-start justify-between gap-3">

                            <h4 className="font-semibold">
                              {gap.title}
                            </h4>

                            <span className="shrink-0 rounded-full bg-amber-950 px-2 py-1 text-xs text-amber-300">
                              {gap.importance}
                            </span>

                          </div>

                          <p className="mt-3 text-sm leading-6 text-slate-400">
                            {gap.description}
                          </p>

                        </article>
                      )
                    )}

                  </div>
                </div>

                {/* DATASETS */}

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                  <p className="text-sm text-cyan-400">
                    Data Intelligence
                  </p>

                  <h3 className="mt-1 text-2xl font-semibold">
                    Recommended Datasets
                  </h3>

                  <div className="mt-5 grid gap-4 md:grid-cols-2">

                    {researchAnalysis.datasets.recommendations.length === 0 ? (
                      <div className="col-span-2 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center">
                        <p className="text-sm text-slate-400">
                          {researchAnalysis.datasets.message || "No exact dataset matching the requested criteria could be verified."}
                        </p>
                      </div>
                    ) : (
                      researchAnalysis.datasets.recommendations.map(
                        (dataset, index) => (
                          <article
                            key={`${dataset.name}-${index}`}
                            className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                          >

                            <h4 className="font-semibold text-slate-100">
                              {dataset.name}
                            </h4>

                            <p className="mt-3 text-sm leading-6 text-slate-400">
                              {dataset.purpose}
                            </p>

                            {dataset.why_matched && (
                              <p className="mt-3 text-xs text-emerald-400/90 font-medium">
                                Match Reason: {dataset.why_matched}
                              </p>
                            )}

                            <p className="mt-4 text-xs text-cyan-400">
                              Source: {dataset.source}
                            </p>

                            <p className="mt-2 text-xs text-slate-500">
                              Use: {dataset.use}
                            </p>

                            {dataset.url ? (
                              <a
                                href={dataset.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-3 inline-block rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-400"
                              >
                                Open Dataset →
                              </a>
                            ) : (
                              <p className="mt-3 text-xs text-slate-500">Source link unavailable</p>
                            )}

                          </article>
                        )
                      )
                    )}

                  </div>

                  {researchAnalysis.datasets.general_repositories && researchAnalysis.datasets.general_repositories.length > 0 && (
                    <div className="mt-8 border-t border-slate-800/80 pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            General Discovery Repositories &amp; Portals
                          </p>
                          <p className="mt-1 text-xs text-slate-400">
                            Explore broad, public data portals if your research requires auxiliary or multi-domain datasets.
                          </p>
                        </div>
                        <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-400">
                          External Portals
                        </span>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        {researchAnalysis.datasets.general_repositories.map((repo, idx) => (
                          <div key={idx} className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-4">
                            <h5 className="font-medium text-sm text-slate-200">{repo.name}</h5>
                            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{repo.purpose}</p>
                            <p className="mt-2 text-[11px] text-slate-500">Source: {repo.source}</p>
                            {repo.url && (
                              <a
                                href={repo.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-3 inline-block text-xs font-medium text-cyan-400 hover:text-cyan-300"
                              >
                                Explore portal →
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* EXPERIMENTS */}

                <div className="rounded-2xl border border-purple-900/40 bg-slate-900 p-6">

                  <p className="text-sm text-purple-400">
                    Experimental Design
                  </p>

                  <h3 className="mt-1 text-2xl font-semibold">
                    Experiment Plan
                  </h3>

                  <div className="mt-5 grid gap-4 lg:grid-cols-2">

                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">

                      <p className="text-sm font-semibold text-purple-300">
                        Baseline
                      </p>

                      <p className="mt-2 text-sm leading-6 text-slate-400">
                        {researchAnalysis.experiments.baseline}
                      </p>

                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">

                      <p className="text-sm font-semibold text-purple-300">
                        Proposed System
                      </p>

                      <p className="mt-2 text-sm leading-6 text-slate-400">
                        {researchAnalysis.experiments.proposed_system}
                      </p>

                    </div>

                  </div>

                  <div className="mt-5 grid gap-4 md:grid-cols-2">

                    {researchAnalysis.experiments.experiments.map(
                      (experiment, index) => (
                        <article
                          key={index}
                          className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                        >

                          <p className="text-xs text-purple-400">
                            EXPERIMENT {index + 1}
                          </p>

                          <h4 className="mt-2 font-semibold">
                            {experiment.name}
                          </h4>

                          <p className="mt-3 text-sm leading-6 text-slate-400">
                            {experiment.objective}
                          </p>

                          <div className="mt-4 flex flex-wrap gap-2">

                            {experiment.metrics.map(
                              (metric, metricIndex) => (
                                <span
                                  key={metricIndex}
                                  className="rounded-full bg-purple-950 px-3 py-1 text-xs text-purple-300"
                                >
                                  {metric}
                                </span>
                              )
                            )}

                          </div>

                        </article>
                      )
                    )}

                  </div>
                </div>

                {/* CHALLENGES, NOVELTY & FUTURE WORK */}

                {(researchAnalysis.plan.expected_challenges || researchAnalysis.plan.potential_novelty || researchAnalysis.plan.future_work) && (
                  <div className="grid gap-6 lg:grid-cols-3">
                    {researchAnalysis.plan.expected_challenges && researchAnalysis.plan.expected_challenges.length > 0 && (
                      <div className="rounded-2xl border border-amber-900/40 bg-slate-900 p-6">
                        <p className="text-sm text-amber-400">Risk Assessment</p>
                        <h3 className="mt-1 text-lg font-semibold">Expected Challenges</h3>
                        <ul className="mt-4 space-y-2">
                          {researchAnalysis.plan.expected_challenges.map((ch, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                              <span className="font-bold text-amber-400">•</span>
                              <span>{ch}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {researchAnalysis.plan.potential_novelty && (
                      <div className="rounded-2xl border border-emerald-900/40 bg-slate-900 p-6">
                        <p className="text-sm text-emerald-400">Research Impact</p>
                        <h3 className="mt-1 text-lg font-semibold">Potential Novelty &amp; Contribution</h3>
                        <p className="mt-4 text-xs leading-relaxed text-slate-300">
                          {researchAnalysis.plan.potential_novelty}
                        </p>
                      </div>
                    )}

                    {researchAnalysis.plan.future_work && researchAnalysis.plan.future_work.length > 0 && (
                      <div className="rounded-2xl border border-purple-900/40 bg-slate-900 p-6">
                        <p className="text-sm text-purple-400">Extensions</p>
                        <h3 className="mt-1 text-lg font-semibold">Future-Work Suggestions</h3>
                        <ul className="mt-4 space-y-2">
                          {researchAnalysis.plan.future_work.map((fw, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                              <span className="font-bold text-purple-400">•</span>
                              <span>{fw}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* ROADMAP */}

                <div className="rounded-2xl border border-cyan-900/50 bg-slate-900 p-6">

                  <p className="text-sm text-cyan-400">
                    AI Research Roadmap
                  </p>

                  <h3 className="mt-1 text-2xl font-semibold">
                    Complete Research Roadmap
                  </h3>

                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    {researchAnalysis.roadmap.analysis_summary}
                  </p>

                  <div className="mt-6 space-y-3">

                    {researchAnalysis.roadmap.milestones.map(
                      (milestone) => (
                        <div
                          key={milestone.step}
                          className="flex gap-4 rounded-xl border border-slate-800 bg-slate-950 p-5"
                        >

                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cyan-950 text-sm font-bold text-cyan-400">
                            {milestone.step}
                          </div>

                          <div>

                            <h4 className="font-semibold">
                              {milestone.title}
                            </h4>

                            <p className="mt-1 text-sm leading-6 text-slate-400">
                              {milestone.description}
                            </p>

                          </div>

                        </div>
                      )
                    )}

                  </div>
                </div>

                {/* OPPORTUNITIES */}

                <div className="rounded-2xl border border-emerald-900/40 bg-slate-900 p-6">

                  <p className="text-sm text-emerald-400">
                    AI Recommendations
                  </p>

                  <h3 className="mt-1 text-2xl font-semibold">
                    Research Opportunities
                  </h3>

                  <div className="mt-5 grid gap-3 md:grid-cols-2">

                    {researchAnalysis.ai_generated_opportunities.map(
                      (opportunity, index) => (
                        <div
                          key={index}
                          className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300"
                        >
                          💡 {opportunity}
                        </div>
                      )
                    )}

                  </div>
                </div>

                {/* EVIDENCE STATUS */}

                <div
                  className={`rounded-xl border p-4 text-sm ${
                    researchAnalysis.evidence_backed
                      ? 'border-emerald-900 bg-emerald-950/30 text-emerald-300'
                      : 'border-amber-900 bg-amber-950/30 text-amber-300'
                  }`}
                >
                  {researchAnalysis.evidence_backed
                    ? '✓ Evidence-backed research analysis generated.'
                    : '⚠ More literature evidence is required.'}
                </div>

              </section>
            )}

            {/* LITERATURE SEARCH — PAGINATED */}
            <section className="mt-10 border-t border-slate-800 pt-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-cyan-400">Literature Search</p>
                  <h2 className="mt-1 text-2xl font-semibold">Search Academic Papers</h2>
                  <p className="mt-1 text-sm text-slate-400">Search directly for academic papers by entering keywords or a specific topic — Semantic Scholar & Crossref, 20-year window, citation-aware scoring.</p>
                  <p className="mt-1 text-xs text-slate-500">Google Scholar public API is unavailable; verified citation counts from Semantic Scholar and Crossref are displayed.</p>
                </div>
              </div>

              <form onSubmit={(e) => { e.preventDefault(); handleLiteratureSearch(1); }} className="mt-5 flex gap-2">
                <input
                  value={litQuery}
                  onChange={(e) => setLitQuery(e.target.value)}
                  placeholder="Enter keywords or a specific research topic... e.g., IoT intrusion detection machine learning"
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-400"
                />
                <button disabled={litSearching || litQuery.trim().length < 2} className="rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 disabled:opacity-50">
                  {litSearching ? 'Searching...' : 'Search Literature'}
                </button>
              </form>

              {litSearching && (
                <div className="mt-5 flex items-center gap-3 rounded-xl border border-cyan-900/60 bg-slate-900/80 p-5">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                  <p className="text-sm text-slate-300">Searching literature providers...</p>
                </div>
              )}

              {litResults && !litSearching && (
                <div className="mt-5">
                  <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
                    <span className="text-sm text-slate-400">
                      {litResults.total} papers found for &ldquo;{litResults.query}&rdquo; — Page {litResults.page}/{litResults.total_pages}
                    </span>
                    <div className="flex items-center gap-3">
                      <label className="text-xs text-slate-500">Sort by:</label>
                      <select
                        value={litSort}
                        onChange={(e) => setLitSort(e.target.value as typeof litSort)}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300 outline-none focus:border-cyan-400"
                      >
                        <option value="relevance">Relevance</option>
                        <option value="citations">Sort by Citations (Semantic Scholar / Crossref)</option>
                        <option value="year-desc">Newest First</option>
                        <option value="year-asc">Oldest First</option>
                      </select>
                      <div className="flex gap-2">
                        <button disabled={litResults.page <= 1} onClick={() => handleLiteratureSearch(litResults.page - 1)} className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 disabled:opacity-40">← Prev</button>
                        <button disabled={litResults.page >= litResults.total_pages} onClick={() => handleLiteratureSearch(litResults.page + 1)} className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 disabled:opacity-40">Next →</button>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {sortedLitResults!.results.map((paper, idx) => (
                      <article key={`${paper.title}-${idx}`} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <h3 className="font-semibold text-slate-100">{paper.title}</h3>
                            <p className="mt-1 text-xs text-slate-500">{paper.authors?.join(', ') || 'Authors unavailable'}{paper.year ? ` • ${paper.year}` : ''}</p>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            {paper.relevance_score != null && (
                              <span className="rounded-full bg-emerald-950 px-2.5 py-1 text-xs font-semibold text-emerald-300">Score {paper.relevance_score}/100</span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                          {(paper.citation_count != null && paper.citation_count > 0) && (
                            <span className="rounded-full bg-amber-950/40 px-2.5 py-0.5 font-medium text-amber-300">
                              Citations: {paper.citation_count.toLocaleString()} · Source: {paper.citation_source || paper.source || 'Semantic Scholar / Crossref'}
                            </span>
                          )}
                          {paper.venue && <span className="text-slate-500">{paper.venue}</span>}
                          {paper.source && <span className="rounded-full bg-blue-950/40 px-2 py-0.5 text-blue-300">{paper.source}</span>}
                          {paper.doi && <span className="text-slate-600">DOI: {paper.doi}</span>}
                        </div>
                        {paper.score_explanation && (
                          <div className="mt-2 rounded-md bg-slate-950 px-3 py-2 text-[10px] text-slate-500">
                            Citation impact: {paper.score_explanation.citation_impact} · Recency: {paper.score_explanation.recency} · Relevance: {paper.score_explanation.topic_relevance}
                          </div>
                        )}
                        {paper.abstract && (
                          <details className="mt-3">
                            <summary className="cursor-pointer text-xs font-medium text-cyan-300">Read abstract</summary>
                            <p className="mt-2 text-xs leading-6 text-slate-400">{paper.abstract}</p>
                          </details>
                        )}
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          {paper.url && <a href={paper.url} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-cyan-400 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300">Read Paper →</a>}
                          <button onClick={() => {
                            createPaper(token!, paper.title, paper.abstract || `Venue: ${paper.venue || 'N/A'} | Year: ${paper.year || 'N/A'} | Citations: ${paper.citation_count} | DOI: ${paper.doi || 'N/A'}`).then((saved) => {
                              setPapers((prev) => [saved, ...prev]);
                            }).catch(() => {});
                          }} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-emerald-500 hover:text-emerald-300">+ Add to Library</button>
                          <button onClick={() => {
                            createPaper(token!, paper.title, paper.abstract || '').then((saved) => {
                              markPaperRecent(token!, saved.id).then((updated) => {
                                setPapers((prev) => [updated, ...prev]);
                              });
                            }).catch(() => {});
                          }} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-purple-500 hover:text-purple-300">★ Recent</button>
                        </div>
                      </article>
                    ))}
                  </div>

                  {/* Pagination */}
                  {litResults.total_pages > 1 && (
                    <div className="mt-5 flex items-center justify-center gap-2">
                      <button disabled={litResults.page <= 1} onClick={() => handleLiteratureSearch(litResults.page - 1)} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-cyan-400 disabled:opacity-40">← Previous</button>
                      <span className="px-4 text-sm text-slate-500">Page {litResults.page} of {litResults.total_pages}</span>
                      <button disabled={litResults.page >= litResults.total_pages} onClick={() => handleLiteratureSearch(litResults.page + 1)} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-cyan-400 disabled:opacity-40">Next →</button>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* RECENT PAPERS */}

            <section className="mt-10 border-t border-slate-800 pt-8">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-purple-400">Quick Access</p>
                  <h2 className="mt-1 text-2xl font-semibold">Recent Papers</h2>
                  <p className="mt-1 text-sm text-slate-400">Papers you&apos;ve starred for quick reference.</p>
                </div>
                <span className="text-sm text-slate-500">{papers.filter((p) => p.is_recent).length} papers</span>
              </div>
              <div className="mt-5 space-y-3">
                {papers.filter((p) => p.is_recent).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 px-6 py-10 text-center text-slate-400">
                    No recent papers yet. Use ★ Recent on search results or evidence cards to star papers here.
                  </div>
                ) : (
                  papers.filter((p) => p.is_recent).map((paper) => (
                    <article key={paper.id} className="rounded-xl border border-purple-900/30 bg-slate-900 p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-slate-100">{paper.title}</h3>
                          <p className="mt-1 text-xs text-slate-500">{paper.authors || 'Authors N/A'}{paper.year ? ` • ${paper.year}` : ''}{paper.venue ? ` • ${paper.venue}` : ''}</p>
                        </div>
                        <button onClick={() => handleToggleRecent(paper.id, true)} className="shrink-0 rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-rose-500 hover:text-rose-400">★ Remove</button>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                        {paper.citation_count > 0 && <span className="rounded-full bg-amber-950/40 px-2 py-0.5 font-medium text-amber-300">Citations: {paper.citation_count}</span>}
                        {paper.doi && <span className="text-slate-600">DOI: {paper.doi}</span>}
                      </div>
                      {paper.abstract && <p className="mt-2 text-xs text-slate-400 line-clamp-2">{paper.abstract}</p>}
                    </article>
                  ))
                )}
              </div>
            </section>

            {/* PAPER LIBRARY */}

            <section className="mt-10 border-t border-slate-800 pt-8">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-cyan-400">Archive</p>
                  <h2 className="mt-1 text-2xl font-semibold">Paper Library</h2>
                  <p className="mt-1 text-sm text-slate-400">All your saved papers and evidence records.</p>
                </div>
                <span className="text-sm text-slate-500">{papers.filter((p) => !p.is_recent).length} papers</span>
              </div>
              <div className="mt-5 space-y-3">
                {papers.filter((p) => !p.is_recent).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 px-6 py-10 text-center text-slate-400">
                    No papers in library. Search literature above and add papers here.
                  </div>
                ) : (
                  papers.filter((p) => !p.is_recent).map((paper) => (
                    <article key={paper.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-slate-100">{paper.title}</h3>
                          <p className="mt-1 text-xs text-slate-500">{paper.authors || 'Authors N/A'}{paper.year ? ` • ${paper.year}` : ''}</p>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <button onClick={() => handleToggleRecent(paper.id, false)} className="rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-purple-500 hover:text-purple-300">★ Add to Recent</button>
                          <button onClick={() => setDeleteConfirmId(paper.id)} className="rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-rose-500 hover:text-rose-400">Delete</button>
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                        {paper.citation_count > 0 && <span className="rounded-full bg-amber-950/40 px-2 py-0.5 font-medium text-amber-300">Citations: {paper.citation_count}</span>}
                        {paper.doi && <span className="text-slate-600">DOI: {paper.doi}</span>}
                      </div>
                      {paper.abstract && <p className="mt-2 text-xs text-slate-400 line-clamp-2">{paper.abstract}</p>}
                      {deleteConfirmId === paper.id && (
                        <div className="mt-3 rounded-lg border border-rose-800 bg-rose-950/40 p-3">
                          <p className="text-xs text-rose-300">Delete this paper?</p>
                          <div className="mt-2 flex gap-2">
                            <button onClick={() => handleDeletePaper(paper.id)} className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white">Confirm</button>
                            <button onClick={() => setDeleteConfirmId(null)} className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-400">Cancel</button>
                          </div>
                        </div>
                      )}
                    </article>
                  ))
                )}
              </div>
            </section>

            {/* REMINDERS */}

            <section className="mt-10 border-t border-slate-800 pt-8">

              <div className="flex items-end justify-between gap-4">

                <div>
                  <p className="text-sm" style={{ color: '#d4a44c' }}>
                    Reminders
                  </p>

                  <h2 className="mt-1 text-2xl font-semibold">
                    Research Reminders
                  </h2>

                  <p className="mt-2 text-sm text-slate-400">
                    Stay on track with your research tasks and deadlines.
                  </p>
                </div>

                <span className="text-sm text-slate-500">
                  {reminders.filter((r) => r.status === 'pending').length} upcoming
                </span>

              </div>

              <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">

                <div className="space-y-3">

                  {reminders.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center">
                      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: 'rgba(105, 76, 197, 0.08)' }}>
                        <span style={{ color: '#7c60d6', fontSize: '1.2rem' }}>⏰</span>
                      </div>
                      <p className="text-base font-semibold" style={{ color: '#1b2440' }}>
                        No reminders yet
                      </p>
                      <p className="mt-1.5 text-sm text-slate-500">
                        Keep your research organized by creating your first reminder.
                      </p>
                    </div>
                  ) : (
                    reminders.map((reminder) => {
                      const isCompleted = reminder.status === 'completed';
                      const isCancelled = reminder.status === 'cancelled';
                      const isSent = reminder.email_sent || reminder.status === 'sent';
                      const isOverdue = !isCompleted && !isCancelled && !isSent && new Date(reminder.reminder_datetime) < new Date();
                      const isDueSoon = !isCompleted && !isCancelled && !isSent && !isOverdue &&
                        (new Date(reminder.reminder_datetime).getTime() - Date.now()) < 86400000;
                      const statusClass = isCompleted ? 'completed' : isCancelled ? 'cancelled' : isSent ? 'sent' : isOverdue ? 'overdue' : isDueSoon ? 'due-soon' : 'upcoming';
                      const statusLabel = isCompleted ? '✓ Completed' : isCancelled ? 'Cancelled' : isSent ? '✓ Email Sent' : isOverdue ? 'Due' : isDueSoon ? 'Due soon' : 'Upcoming';

                      return (
                        <article
                          key={reminder.id}
                          className={`reminder-card status-${statusClass}`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0">
                              <h3 className="font-semibold" style={{ color: '#1b2440' }}>
                                {reminder.title}
                              </h3>

                              {reminder.description && (
                                <p className="mt-1.5 text-sm text-slate-500">
                                  {reminder.description}
                                </p>
                              )}

                              <p className="mt-2.5 text-xs text-slate-500">
                                {isCompleted
                                  ? `Completed ${new Date(reminder.updated_at).toLocaleDateString()}`
                                  : `Scheduled for: ${formatReminderDate(reminder.reminder_datetime, reminder.timezone)} (${reminder.timezone || 'Asia/Kolkata'})`
                                }
                              </p>

                              {reminder.email_sent && reminder.email_sent_at && (
                                <p className="mt-1 text-xs text-indigo-600 font-medium">
                                  Email dispatched: {new Date(reminder.email_sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                              )}

                              {reminder.last_error && (
                                <p className="mt-1 text-xs text-red-500">
                                  Delivery issue: {reminder.last_error}
                                </p>
                              )}
                            </div>

                            <span className={`reminder-status-badge shrink-0 ${statusClass}`}>
                              {statusLabel}
                            </span>
                          </div>

                          {!isCompleted && !isCancelled && (
                            <div className="mt-4 flex flex-wrap gap-2">
                              <button
                                onClick={() => handleCompleteReminder(reminder.id)}
                                className="rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition"
                                style={{ background: 'linear-gradient(135deg, #6d4fd2, #8d70ed)' }}
                              >
                                Mark complete
                              </button>
                              <button
                                onClick={() => handleCancelReminder(reminder.id)}
                                className="rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs font-medium text-amber-700 transition hover:bg-amber-100"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleDeleteReminder(reminder.id)}
                                className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs text-slate-600 transition hover:border-[#d66060] hover:text-[#d66060]"
                              >
                                Delete
                              </button>
                            </div>
                          )}

                        </article>
                      );
                    })

                  )}

                </div>

                <form
                  onSubmit={handleCreateReminder}
                  className="h-fit rounded-xl border border-slate-800 bg-slate-900 p-5"
                >

                  <h2 className="font-semibold">
                    Add a reminder
                  </h2>

                  <p className="mt-2 text-sm text-slate-400">
                    Never miss a research deadline.
                  </p>

                  <div className="mt-5 space-y-3">

                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-500">Title</label>
                      <input
                        required
                        minLength={1}
                        value={reminderTitle}
                        onChange={(event) => setReminderTitle(event.target.value)}
                        placeholder="e.g., Review literature"
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-500">Notes</label>
                      <textarea
                        value={reminderDescription}
                        onChange={(event) => setReminderDescription(event.target.value)}
                        placeholder="Optional description"
                        rows={3}
                        className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-500">Date & time</label>
                      <input
                        required
                        type="datetime-local"
                        value={reminderDatetime}
                        onChange={(event) => setReminderDatetime(event.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-500">Timezone</label>
                      <select
                        value={reminderTimezone}
                        onChange={(event) => setReminderTimezone(event.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-cyan-400 text-slate-200"
                      >
                        <option value="Asia/Kolkata">Asia/Kolkata (IST — India Standard Time)</option>
                        <option value="UTC">UTC (Coordinated Universal Time)</option>
                        <option value="America/New_York">America/New_York (EST / EDT)</option>
                        <option value="Europe/London">Europe/London (GMT / BST)</option>
                      </select>
                    </div>

                    <button
                      className="w-full rounded-lg px-4 py-3 text-sm font-semibold text-white transition"
                      style={{ background: 'linear-gradient(135deg, #6d4fd2, #8d70ed)' }}
                    >
                      Create reminder
                    </button>

                  </div>

                </form>

              </div>

            </section>

            {/* NOTIFICATIONS */}

            <section className="mt-10 border-t border-slate-800 pt-8">

              <p className="text-sm text-slate-500">
                Updates
              </p>

              <h2 className="mt-1 text-2xl font-semibold">
                Notifications
              </h2>

              <div className="mt-5 space-y-3">

                {notifications.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 px-6 py-10 text-center text-slate-400">
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map(
                    (notification) => (
                      <article
                        key={notification.id}
                        className="rounded-xl border border-slate-800 bg-slate-900 p-5"
                      >

                        <div className="flex items-start justify-between gap-4">

                          <div>
                            <p className="text-sm text-cyan-400">
                              {notification.type}
                            </p>

                            <p className="mt-1 text-sm text-slate-300">
                              {notification.message}
                            </p>
                          </div>

                          {!notification.read_at && (
                            <button
                              onClick={() =>
                                handleMarkRead(
                                  notification.id
                                )
                              }
                              className="text-xs text-slate-500 hover:text-cyan-400"
                            >
                              Mark read
                            </button>
                          )}

                        </div>

                      </article>
                    )
                  )
                )}

              </div>
            </section>
          </>
        )}
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
