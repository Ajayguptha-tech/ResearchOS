"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const data = await login(email, password);

      localStorage.setItem("access_token", data.access_token);

      // Go directly to dashboard (no email verification required)
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="flex min-h-screen items-center justify-center px-5">

        <div className="w-full max-w-md">

          {/* Brand */}
          <div className="mb-8 text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: '#664bc5' }}>
              RESEARCHOS
            </p>

            <h1 className="mt-3 text-2xl font-bold tracking-tight" style={{ color: '#1b2440' }}>
              Welcome back
            </h1>

            <p className="mt-2 text-sm" style={{ color: '#68728a' }}>
              Sign in to continue your research.
            </p>
          </div>

          {/* Login Card */}
          <div className="rounded-2xl border border-[#e6e0f8] bg-white p-8 shadow-lg" style={{ boxShadow: '0 20px 50px rgba(67, 47, 137, 0.08)' }}>

            <form onSubmit={handleLogin} className="space-y-5">

              {/* Email */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: '#4e5871' }}>
                  Email
                </label>

                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                  style={{ color: '#1d2742' }}
                />
              </div>

              {/* Password */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: '#4e5871' }}>
                  Password
                </label>

                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                  style={{ color: '#1d2742' }}
                />
              </div>

              {/* Forgot Password */}
              <div className="text-right">
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium transition"
                  style={{ color: '#664bc5' }}
                >
                  Forgot password?
                </Link>
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-sm" style={{ color: '#b44c4c' }}>
                  <p>{error}</p>
                  {error.toLowerCase().includes("verify your email") && (
                    <button
                      type="button"
                      onClick={() => {
                        localStorage.setItem("verify_email", email.trim().toLowerCase());
                        router.push("/verify-email");
                      }}
                      className="mt-2 text-xs font-semibold underline"
                      style={{ color: "#6247bf" }}
                    >
                      Enter verification code →
                    </button>
                  )}
                </div>
              )}

              {/* Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                style={{ boxShadow: '0 9px 18px rgba(97, 70, 190, 0.18)' }}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Signing in…
                  </span>
                ) : "Sign in"}
              </button>

              {/* Demo Credentials Quick Fill */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setEmail("demo@researchos.io");
                    setPassword("DemoPassword123!");
                  }}
                  className="w-full rounded-xl border border-[#e0d9f4] bg-[#faf8ff] px-4 py-2.5 text-xs font-semibold text-[#6247bf] transition hover:bg-[#f0ebff]"
                >
                  ⚡ Quick Fill Demo Account (demo@researchos.io)
                </button>
              </div>

            </form>

          </div>

          <p className="mt-6 text-center text-xs" style={{ color: '#8790a4' }}>
            Don&apos;t have an account?{' '}
            <Link href="/register" className="font-medium" style={{ color: '#664bc5' }}>
              Create Account
            </Link>
          </p>

          <p className="mt-3 text-center text-xs" style={{ color: '#8790a4' }}>
            ResearchOS · AI Research Intelligence Platform
          </p>

        </div>

      </div>
    </main>
  );
}