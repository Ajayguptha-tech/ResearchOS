"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe, listPapers, listProjects } from "../../lib/api";
import type { Paper, Project, UserProfile } from "../../lib/api";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const token = localStorage.getItem("access_token");

        if (!token) {
          window.location.href = '/login';
          return;
        }

        const [profileData, projectData, paperData] = await Promise.allSettled([
          getMe(token),
          listProjects(token),
          listPapers(token),
        ]);
        // Detect invalid token and clear it
        const firstAuthFailure = [profileData, projectData, paperData]
          .find((r): r is PromiseRejectedResult => r.status === 'rejected' && r.reason instanceof Error && (r.reason.message === 'Invalid token' || r.reason.message === 'Authentication required'));
        if (firstAuthFailure) {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
          return;
        }
        if (profileData.status === 'fulfilled') setUserProfile(profileData.value);
        if (projectData.status === 'fulfilled') setProjects(projectData.value);
        if (paperData.status === 'fulfilled') setPapers(paperData.value);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load projects."
        );
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const displayName = userProfile?.name || 'there';

  if (loading) {
    return (
      <main className="auth-page flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: "#664bc5" }}>
            RESEARCHOS
          </p>
          <div className="mt-4 flex items-center justify-center gap-1.5">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="research-shell min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-8">

        {/* Header */}
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-cyan-400">
              RESEARCHOS
            </p>

            <h1 className="mt-2 text-4xl font-bold">
              Welcome back{userProfile ? `, ${displayName}` : ''} 👋
            </h1>

            <p className="mt-2 text-slate-400">
              Turn your research ideas into evidence-backed research plans.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/workspace"
              className="rounded-xl border border-slate-700 px-5 py-3 font-semibold text-slate-300 transition hover:border-cyan-400 hover:text-white"
            >
              Open Workspace
            </Link>
            <Link
              href="/research/new"
              className="rounded-xl bg-cyan-500 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-400"
            >
              + New Project
            </Link>
          </div>
        </div>

        {/* Statistics */}
        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">
              Research Projects
            </p>

            <p className="mt-3 text-3xl font-bold">
              {loading ? "..." : projects.length}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Total projects
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">
              Papers
            </p>

            <p className="mt-3 text-3xl font-bold">
              {loading ? "..." : papers.length}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Evidence library
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">
              Datasets
            </p>

            <p className="mt-3 text-3xl font-bold">
              {loading ? "..." : 0}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Recommended datasets
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">
              Research Progress
            </p>

            <p className="mt-3 text-3xl font-bold">
              {loading ? "..." : "0%"}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Overall progress
            </p>
          </div>

        </section>

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300">
            {error}
          </div>
        )}

        {/* Projects */}
        <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">

          <h2 className="text-2xl font-semibold">
            Your Research Projects
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Projects loaded from the ResearchOS backend.
          </p>

          {loading && (
            <p className="mt-6 text-slate-400">
              Loading projects...
            </p>
          )}

          {!loading && projects.length === 0 && !error && (
            <div className="mt-6 rounded-xl border border-dashed border-slate-700 p-8 text-center">

              <p className="text-lg font-semibold">
                No research projects yet
              </p>

              <p className="mt-2 text-sm text-slate-500">
                Create your first research project.
              </p>

            </div>
          )}

          {!loading && projects.length > 0 && (
            <div className="mt-6 grid gap-4 md:grid-cols-2">

              {projects.map((project) => (
                <div
                  key={project.id}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                >

                  <div className="flex items-start justify-between">

                    <div>
                      <h3 className="text-lg font-semibold">
                        {project.title}
                      </h3>

                      <p className="mt-2 text-sm text-slate-400">
                        {project.domain}
                      </p>
                    </div>

                    <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300">
                      {project.status}
                    </span>

                  </div>

                  <p className="mt-5 text-xs text-slate-500">
                    Project #{project.id}
                  </p>

                  <Link
                    href={`/workspace/${project.id}`}
                    className="mt-4 inline-block text-sm text-cyan-400 hover:text-cyan-300"
                  >
                    Open workspace →
                  </Link>

                </div>
              ))}

            </div>
          )}

        </section>

        {/* AI Modules */}
        <section className="mt-8">

          <h2 className="text-2xl font-semibold">
            Research Intelligence
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Core AI capabilities of ResearchOS.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-5">

            {["Semantic Retrieval",
              "Paper Summarization",
              "Research Gap Analysis",
              "Dataset Recommendation",
              "Experiment Planning",
            ].map((module) => (
              <div
                key={module}
                className="rounded-xl border border-slate-800 bg-slate-900 p-5 hover:border-cyan-500/40"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400">
                  AI
                </div>

                <p className="text-sm font-medium">
                  {module}
                </p>

                <p className="mt-2 text-xs text-slate-500">
                  Evidence-driven research assistance.
                </p>
              </div>
            ))}

          </div>

        </section>

      </div>
    </main>
  );
}
