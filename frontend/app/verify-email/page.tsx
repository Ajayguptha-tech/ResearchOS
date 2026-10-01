"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { resendOtp, verifyEmail } from "../../lib/api";

export default function VerifyEmailPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(60);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const [emailStatus, setEmailStatus] = useState("");
  const [emailDetail, setEmailDetail] = useState("");
  const [verifyToken, setVerifyToken] = useState("");

  useEffect(() => {
    const storedEmail = localStorage.getItem("verify_email");
    if (storedEmail) setEmail(storedEmail);
    const status = localStorage.getItem("email_status");
    const detail = localStorage.getItem("email_detail");
    const token = localStorage.getItem("verify_token");
    if (status) setEmailStatus(status);
    if (detail) setEmailDetail(detail);
    if (token) setVerifyToken(token);
  }, []);

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

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
      if (pasted) {
        const newOtp = pasted.split("").concat(Array(6).fill("")).slice(0, 6);
        setOtp(newOtp);
        const nextEmpty = newOtp.findIndex((v) => !v);
        inputRefs.current[nextEmpty >= 0 ? nextEmpty : 5]?.focus();
      }
    },
    []
  );

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    const otpString = otp.join("");
    if (otpString.length !== 6 || !email) return;
    setLoading(true);
    setError("");
    try {
      await verifyEmail(email, otpString, verifyToken || undefined);
      localStorage.removeItem("verify_email");
      localStorage.removeItem("verify_token");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!email || countdown > 0) return;
    setResending(true);
    setError("");
    try {
      await resendOtp(email, verifyToken || undefined);
      setCountdown(60);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend code.");
    } finally {
      setResending(false);
    }
  }

  if (success) {
    return (
      <main className="auth-page">
        <div className="flex min-h-screen items-center justify-center px-5">
          <div className="w-full max-w-md">
            <div className="rounded-2xl border border-[#e6e0f8] bg-white p-10 text-center shadow-lg">
              <div className="success-check" aria-hidden="true">✓</div>
              <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#1b2440" }}>
                Email Verified!
              </h1>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: "#68728a" }}>
                Your email has been verified successfully. You now have full
                access to all ResearchOS features.
              </p>
              <button
                onClick={() => router.push("/workspace")}
                className="mt-8 w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8]"
                style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
              >
                Go to Workspace
              </button>
            </div>
            <p className="mt-5 text-center text-xs" style={{ color: "#8790a4" }}>
              ResearchOS · AI Research Intelligence Platform
            </p>
          </div>
        </div>
      </main>
    );
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
              Verify your email
            </h1>
            <p className="mt-2 text-sm" style={{ color: "#68728a" }}>
              Enter the 6-digit code we sent to your email address.
            </p>
          </div>

          {/* Step indicator */}
          <div className="auth-steps">
            <div className="auth-step-dot completed" />
            <div className="auth-step-line completed" />
            <div className="auth-step-dot active" />
            <div className="auth-step-line" />
            <div className="auth-step-dot" />
          </div>

          {/* Verification card */}
          <div className="rounded-2xl border border-[#e6e0f8] bg-white p-8 shadow-lg" style={{ boxShadow: "0 20px 50px rgba(67, 47, 137, 0.08)" }}>

            {email && (
              <div className="mb-6 text-center">
                <p className="text-sm" style={{ color: "#68728a" }}>
                  Code sent to <span className="font-medium" style={{ color: "#1d2742" }}>{email}</span>
                </p>
                {emailStatus === "logged" && (
                  <p className="mt-2 rounded-lg border border-[rgba(210,170,60,0.3)] bg-[rgba(210,170,60,0.06)] px-3 py-2 text-xs" style={{ color: "#8a7030" }}>
                    Development mode: OTP is printed in the backend terminal. Check the server logs for your code.
                  </p>
                )}
                {emailStatus === "failed" && (
                  <p className="mt-2 rounded-lg border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-3 py-2 text-xs" style={{ color: "#b44c4c" }}>
                    Email delivery failed. {emailDetail || "Check SMTP configuration in backend/.env"}
                  </p>
                )}
              </div>
            )}

            {!email && (
              <div className="mb-5">
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
            )}

            <form onSubmit={handleVerify} className="space-y-6">

              {/* OTP input */}
              <div>
                <label className="mb-3 block text-center text-sm font-medium" style={{ color: "#4e5871" }}>
                  Verification Code
                </label>
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
                      aria-label={`Digit ${index + 1} of verification code`}
                    />
                  ))}
                </div>
              </div>

              {/* Countdown */}
              <div className="flex justify-center">
                {countdown > 0 ? (
                  <span className="countdown-pill">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/>
                      <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    Code expires in {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                  </span>
                ) : (
                  <span className="text-xs" style={{ color: "#8790a4" }}>
                    Code expired — resend below
                  </span>
                )}
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-xl border border-[rgba(180,76,76,0.25)] bg-[rgba(180,76,76,0.06)] px-4 py-3 text-center text-sm" style={{ color: "#b44c4c" }}>
                  {error}
                </div>
              )}

              {/* Verify button */}
              <button
                type="submit"
                disabled={loading || otp.join("").length !== 6 || !email}
                className="w-full rounded-xl bg-[#6247bf] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#5538a8] disabled:cursor-not-allowed disabled:opacity-50"
                style={{ boxShadow: "0 9px 18px rgba(97, 70, 190, 0.18)" }}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Verifying…
                  </span>
                ) : (
                  "Verify Email"
                )}
              </button>
            </form>

            {/* Resend */}
            <div className="mt-6 text-center">
              <span className="text-sm" style={{ color: "#8790a4" }}>
                Didn&apos;t receive a code?{" "}
              </span>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending || countdown > 0}
                className="text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
                style={{ color: "#664bc5" }}
              >
                {countdown > 0
                  ? "Resend available soon"
                  : resending
                  ? "Sending…"
                  : "Resend code"}
              </button>
            </div>
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
