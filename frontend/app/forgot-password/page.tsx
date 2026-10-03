"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  forgotPassword,
  resetPassword,
  verifyResetOtp,
} from "../../lib/api";

type Step = "email" | "verify" | "reset" | "success";

const STEP_LABELS: Record<Step, { title: string; subtitle: string }> = {
  email: {
    title: "Reset your password",
    subtitle: "Enter the email address associated with your ResearchOS account.",
  },
  verify: {
    title: "Verify your identity",
    subtitle: "Enter the 6-digit code we sent to your email.",
  },
  reset: {
    title: "Create new password",
    subtitle: "Choose a strong password for your account.",
  },
  success: {
    title: "Password reset!",
    subtitle: "Your password has been updated successfully.",
  },
};

export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const isSubmittingRef = useRef(false);
  const isResendingRef = useRef(false);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleOtpChange = useCallback(
    (index: number, value: string) => {
      if (!/^\d*$/.test(value)) return;
      const newOtp = [...otp];
      newOtp[index] = value.slice(-1);
      setOtp(newOtp);
      if (value && index < 5) inputRefs.current[index + 1]?.focus();
    },
    [otp]
  );

  const handleOtpKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent) => {
      if (e.key === "Backspace" && !otp[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
    },
    [otp]
  );

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted) {
      const newOtp = pasted.split("").concat(Array(6).fill("")).slice(0, 6);
      setOtp(newOtp);
      const nextEmpty = newOtp.findIndex((v) => !v);
      inputRefs.current[nextEmpty >= 0 ? nextEmpty : 5]?.focus();
    }
  }, []);

  // Password strength indicator
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

  const strength = newPassword ? getPasswordStrength(newPassword) : null;

  const stepIndex = step === "email" ? 0 : step === "verify" ? 1 : step === "reset" ? 2 : 3;

  async function handleRequestReset(e: React.FormEvent) {
    e.preventDefault();
    if (!email || isSubmittingRef.current || loading) return;
    isSubmittingRef.current = true;
    setLoading(true);
    setError("");
    try {
      await forgotPassword(email);
      setStep("verify");
      setCountdown(60);
      setOtp(["", "", "", "", "", ""]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset code.");
    } finally {
      setLoading(false);
      isSubmittingRef.current = false;
    }
  }

  async function handleResendCode() {
    if (!email || countdown > 0 || isResendingRef.current || resending) return;
    isResendingRef.current = true;
    setResending(true);
    setError("");
    try {
      await forgotPassword(email);
      setCountdown(60);
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend code.");
    } finally {
      setResending(false);
      isResendingRef.current = false;
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    const otpString = otp.join("");
    if (otpString.length !== 6) return;
    setLoading(true);
    setError("");
    try {
      await verifyResetOtp(email, otpString);
      setStep("reset");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (newPassword !== confirmPassword) { setError("Passwords do not match."); return; }
    setLoading(true);
    setError("");
    try {
      await resetPassword(email, otp.join(""), newPassword);
      setStep("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password reset failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="flex min-h-screen items-center justify-center px-5">
        <div className="w-full max-w-md">

          {/* Brand header */}
          <div className="mb-8 text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: "#664bc5" }}>
              ResearchOS
            </p>
            <h1 className="mt-3 text-2xl font-bold tracking-tight" style={{ color: "#1b2440" }}>
              {STEP_LABELS[step].title}
            </h1>
            <p className="mt-2 text-sm leading-relaxed" style={{ color: "#68728a" }}>
              {STEP_LABELS[step].subtitle}
            </p>
          </div>

          {/* Step indicator */}
          {step !== "success" && (
            <div className="auth-steps">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className={`auth-step-dot ${i < stepIndex ? "completed" : i === stepIndex ? "active" : ""}`} />
                  {i < 2 && <div className={`auth-step-line ${i < stepIndex ? "completed" : ""}`} />}
                </div>
              ))}
            </div>
          )}

          {/* Card */}
          <div className="rounded-2xl border border-[#e6e0f8] bg-white p-8 shadow-lg" style={{ boxShadow: "0 20px 50px rgba(67, 47, 137, 0.08)" }}>

            {/* Step 1: Email */}
            {step === "email" && (
              <form onSubmit={handleRequestReset} className="space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>
                    Email address
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
                {error && (
                  <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-sm" style={{ color: "#b44c4c" }}>
                    {error}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
                >
                  {loading ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Sending…
                    </span>
                  ) : "Send Reset Code"}
                </button>
              </form>
            )}

            {/* Step 2: Verify OTP */}
            {step === "verify" && (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                <p className="text-center text-sm" style={{ color: "#68728a" }}>
                  Code sent to <span className="font-medium" style={{ color: "#1d2742" }}>{email}</span>
                </p>
                <div>
                  <div className="flex justify-center gap-2.5">
                    {otp.map((digit, index) => (
                      <input
                        key={index}
                        ref={(el) => { inputRefs.current[index] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
                        onPaste={handlePaste}
                        className={`otp-input ${digit ? "filled" : ""} ${error ? "error" : ""}`}
                        aria-label={`Digit ${index + 1}`}
                      />
                    ))}
                  </div>
                </div>
                {countdown > 0 && (
                  <div className="flex justify-center">
                    <span className="countdown-pill">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                      </svg>
                      Resend in {countdown}s
                    </span>
                  </div>
                )}
                {error && (
                  <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-center text-sm" style={{ color: "#b44c4c" }}>
                    {error}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading || otp.join("").length !== 6}
                  className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
                >
                  {loading ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Verifying…
                    </span>
                  ) : "Verify Code"}
                </button>
                {countdown <= 0 && (
                  <div className="text-center">
                    <button
                      type="button"
                      disabled={resending || countdown > 0}
                      onClick={handleResendCode}
                      className="text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
                      style={{ color: "#664bc5" }}
                    >
                      {resending ? "Sending new code…" : "Resend code"}
                    </button>
                  </div>
                )}
              </form>
            )}

            {/* Step 3: New Password */}
            {step === "reset" && (
              <form onSubmit={handleResetPassword} className="space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter new password"
                    required
                    minLength={8}
                    className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                    style={{ color: "#1d2742" }}
                  />
                  {/* Password strength bar */}
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
                <div>
                  <label className="mb-2 block text-sm font-medium" style={{ color: "#4e5871" }}>Confirm Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm your new password"
                    required
                    minLength={8}
                    className="w-full rounded-xl border border-[#e0d9f4] bg-white px-4 py-3 text-sm outline-none transition"
                    style={{ color: "#1d2742" }}
                  />
                  {confirmPassword && newPassword !== confirmPassword && (
                    <p className="mt-1.5 text-xs" style={{ color: "#b44c4c" }}>Passwords do not match</p>
                  )}
                </div>
                {error && (
                  <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-sm" style={{ color: "#b44c4c" }}>
                    {error}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
                >
                  {loading ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Resetting…
                    </span>
                  ) : "Reset Password"}
                </button>
              </form>
            )}

            {/* Step 4: Success */}
            {step === "success" && (
              <div className="text-center">
                <div className="success-check mx-auto" aria-hidden="true">✓</div>
                <p className="text-sm leading-relaxed" style={{ color: "#68728a" }}>
                  Your password has been updated. You can now sign in with your
                  new credentials.
                </p>
                <button
                  onClick={() => router.push("/login")}
                  className="mt-8 w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8]"
                  style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
                >
                  Go to Sign In
                </button>
              </div>
            )}
          </div>

          {/* Back link */}
          <p className="mt-6 text-center text-xs" style={{ color: "#8790a4" }}>
            <button
              onClick={() => router.push("/login")}
              className="font-medium transition"
              style={{ color: "#664bc5" }}
            >
              ← Back to sign in
            </button>
          </p>
        </div>
      </div>
    </main>
  );
}
