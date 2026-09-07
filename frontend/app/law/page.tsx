'use client';

import { FormEvent, useEffect, useState } from 'react';

import { addLawSource, createLawProject, LawProject, LawSource, listLawProjects, listLawSources } from '../../lib/api';

export default function LawPage() {
  const [token, setToken] = useState<string | null>(null);
  const [projects, setProjects] = useState<LawProject[]>([]);
  const [sources, setSources] = useState<LawSource[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const savedToken = window.localStorage.getItem('access_token');
    if (!savedToken) return;
    setToken(savedToken);
    listLawProjects(savedToken).then((loaded) => {
      setProjects(loaded);
      if (loaded[0]) {
        setSelectedProject(loaded[0].id);
        return listLawSources(savedToken, loaded[0].id);
      }
      return [];
    }).then(setSources).catch((loadError) => setError(loadError instanceof Error ? loadError.message : 'Unable to load legal research.'));
  }, []);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const form = new FormData(event.currentTarget);
    try {
      const project = await createLawProject(token, String(form.get('title')), String(form.get('question')), String(form.get('jurisdiction')));
      setProjects((current) => [project, ...current]);
      setSelectedProject(project.id);
      setSources([]);
      event.currentTarget.reset();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Unable to create legal research project.');
    }
  }

  async function selectProject(projectId: number) {
    if (!token) return;
    setSelectedProject(projectId);
    try {
      setSources(await listLawSources(token, projectId));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load legal sources.');
    }
  }

  async function createSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !selectedProject) return;
    const form = new FormData(event.currentTarget);
    try {
      const source = await addLawSource(token, selectedProject, String(form.get('label')), String(form.get('url')), String(form.get('type')) as LawSource['source_type'], String(form.get('excerpt')));
      setSources((current) => [...current, source]);
      event.currentTarget.reset();
    } catch (sourceError) {
      setError(sourceError instanceof Error ? sourceError.message : 'Unable to save legal source.');
    }
  }

  if (!token) {
    return <main className="research-shell min-h-screen bg-slate-950 p-8 text-slate-50"><div className="mx-auto max-w-3xl"><h1 className="text-3xl font-bold">Legal Research</h1><p className="mt-4 text-slate-400">Sign in from the workspace before opening a legal research matter.</p></div></main>;
  }

  return <main className="research-shell min-h-screen bg-slate-950 p-6 text-slate-50 sm:p-10"><div className="mx-auto max-w-6xl"><p className="text-sm font-medium uppercase tracking-[0.2em] text-violet-300">ResearchOS / Law</p><h1 className="mt-3 text-4xl font-bold tracking-tight">Legal research workspace</h1><p className="mt-3 max-w-3xl text-slate-400">Organize legal questions and source-backed authorities in a private research matter.</p><p className="mt-4 rounded-lg border border-amber-900/60 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">Research assistance only - not legal advice.</p>{error && <p role="alert" className="mt-5 rounded-lg border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">{error}</p>}<div className="mt-8 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]"><aside className="rounded-xl border border-slate-800 bg-slate-900 p-5"><h2 className="font-semibold">Matters</h2><div className="mt-4 space-y-2">{projects.map((project) => <button key={project.id} onClick={() => selectProject(project.id)} className={`w-full rounded-lg border p-3 text-left text-sm ${selectedProject === project.id ? 'border-cyan-400 bg-cyan-950/40' : 'border-slate-800 hover:border-cyan-900'}`}><span className="font-medium">{project.title}</span><span className="mt-1 block text-xs text-slate-500">{project.jurisdiction || 'Jurisdiction not specified'}</span></button>)}</div><form onSubmit={createProject} className="mt-6 space-y-3 border-t border-slate-800 pt-5"><input name="title" required minLength={3} placeholder="Matter title" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><input name="jurisdiction" placeholder="Jurisdiction" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><textarea name="question" required minLength={10} placeholder="Legal question" rows={4} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><button className="w-full rounded-lg bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950">Create matter</button></form></aside><section className="rounded-xl border border-slate-800 bg-slate-900 p-5"><h2 className="text-xl font-semibold">Source register</h2>{selectedProject ? <><p className="mt-2 text-sm text-slate-400">Only user-provided source records are shown. Every record keeps its provenance classification.</p><div className="mt-5 space-y-3">{sources.length === 0 ? <p className="rounded-lg border border-dashed border-slate-700 p-8 text-center text-slate-500">No sources recorded for this matter.</p> : sources.map((source) => <article key={source.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><div className="flex justify-between gap-4"><h3 className="font-medium">{source.label}</h3><span className="text-xs uppercase text-violet-300">{source.source_type}</span></div><a className="mt-2 block break-all text-sm text-cyan-400" href={source.source_url} target="_blank" rel="noreferrer">{source.source_url}</a>{source.excerpt && <p className="mt-3 text-sm text-slate-400">{source.excerpt}</p>}</article>)}</div><form onSubmit={createSource} className="mt-6 grid gap-3 border-t border-slate-800 pt-5 md:grid-cols-2"><input name="label" required minLength={3} placeholder="Source label" className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><input name="url" required type="url" placeholder="https://..." className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><select name="type" className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"><option value="source">Source</option><option value="fact">Fact</option><option value="inference">Inference</option><option value="suggestion">Suggestion</option></select><textarea name="excerpt" placeholder="User-provided excerpt" rows={3} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /><button className="rounded-lg bg-white px-3 py-2 text-sm font-semibold text-slate-950 md:col-span-2">Add source record</button></form></> : <p className="mt-6 text-slate-400">Create a legal research matter to begin.</p>}</section></div></div></main>;
}