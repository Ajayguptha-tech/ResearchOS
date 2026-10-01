"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createProject } from "../../../lib/api";

export default function NewResearchProjectPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        router.push("/login");
        return;
      }

      await createProject(token, title, domain);

      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : '';
      if (msg === 'Invalid token' || msg === 'Authentication required') {
        localStorage.removeItem('access_token');
        router.push('/login');
        return;
      }
      setError(msg || 'Unable to create research project.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto max-w-3xl px-6 py-10">

        <button
          onClick={() => router.back()}
          className="mb-8 text-sm text-cyan-400 hover:text-cyan-300"
        >
          ← Back
        </button>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8">

          <p className="text-sm font-medium text-cyan-400">
            RESEARCHOS
          </p>

          <h1 className="mt-2 text-3xl font-bold">
            Create Research Project
          </h1>

          <p className="mt-2 text-slate-400">
            Start a new evidence-backed research project.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-6">

            {/* Project Title */}
            <div>
              <label className="mb-2 block text-sm font-medium">
                Research Project Title
              </label>

              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="AI Research & Project Collaboration Agent"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-500"
              />
            </div>

            {/* Domain */}
            <div>
              <label className="mb-2 block text-sm font-medium">
                Research Domain
              </label>

              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="GenAI · Research Intelligence · Knowledge Graphs"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-500"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-cyan-500 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
            >
              {loading ? "Creating project..." : "Create Research Project"}
            </button>

          </form>
        </div>

      </div>
    </main>
  );
}