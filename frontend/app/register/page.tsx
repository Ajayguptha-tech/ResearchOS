"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Password strength
  function getPasswordStrength(pw: string): { label: string; color: string; width: string } {
    if (pw.length < 8) return { label: "Too short", color: "#d66060", width: "20%" };
    let score = 0;
    if (/[a-z]/.test(pw)) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^a-zA-Z0-9]/.test(pw)) score++;
    if (pw.length >= 12) score++;
    if (score <= 2) return { label: "Weak", color: "#d4a44c", width: "40%" };
    if (score <= 3) return { label: "Fair", color: "#b89a3a", width: "60%" };
    if (score <= 4) return { label: "Strong", color: "#6ab89a", width: "85%" };
    return { label: "Very strong", color: "#3a8c6a", width: "100%" };
  }

  const strength = password ? getPasswordStrength(password) : null;

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await register(email, password, name);
      // Store the access token and go directly to dashboard
      // (no email verification required)
      localStorage.setItem("access_token", result.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Registration failed. Please try again."
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
            <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: "#664bc5" }}>
              RESEARCHOS
            </p>
            <h1 className="mt-3 text-2xl font-bold tracking-tight" style={{ color: "#1b2440" }}>
              Create your account
            </h1>
            <p className="mt-2 text-sm" style={{ color: "#68728a" }}>
              Start your research journey with ResearchOS.
            </p>
          </div>

          {/* Register Card */}
          <div className="rounded-2xl border border-[#e6e0f8] bg-white p-8 shadow-lg" style={{ boxShadow: "0 20px 50px rgba(67, 47, 137, 0.08)" }}>
            <form onSubmit={handleRegister} className="space-y-5">
              {/* Name */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your full name"
                  required
                  minLength={2}
                  className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                  style={{ color: "#1d2742" }}
                />
              </div>

              {/* Email */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                  style={{ color: "#1d2742" }}
                />
              </div>

              {/* Password */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    minLength={8}
                    className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 pr-12 text-sm outline-none transition"
                    style={{ color: "#1d2742" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium"
                    style={{ color: "#8790a4" }}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {strength && (
                  <div className="mt-2.5">
                    <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "#f0edff" }}>
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: strength.width, background: strength.color }}
                      />
                    </div>
                    <p className="mt-1 text-xs font-medium" style={{ color: strength.color }}>
                      {strength.label}
                    </p>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                  minLength={8}
                  className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                  style={{ color: "#1d2742" }}
                />
                {confirmPassword && password !== confirmPassword && (
                  <p className="mt-1.5 text-xs" style={{ color: "#b44c4c" }}>
                    Passwords do not match
                  </p>
                )}
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-sm" style={{ color: "#b44c4c" }}>
                  {error}
                </div>
              )}

              {/* Button */}
              <button
                type="submit"
                disabled={loading || !name || !email || !password || password !== confirmPassword}
                className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Creating account…
                  </span>
                ) : "Create Account"}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs" style={{ color: "#8790a4" }}>
            Already have an account?{" "}
            <Link href="/login" className="font-medium" style={{ color: "#664bc5" }}>
              Sign in
            </Link>
          </p>

          <p className="mt-3 text-center text-xs" style={{ color: "#8790a4" }}>
            ResearchOS · AI Research Intelligence Platform
          </p>
        </div>
      </div>
    </main>
  );
}
