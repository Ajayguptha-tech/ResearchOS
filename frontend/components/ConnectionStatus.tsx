"use client";

import { useEffect, useState } from "react";

export function ConnectionStatus() {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setMounted(true);
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!mounted) {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full border border-[#e0d9f4] bg-white px-2.5 py-1 text-xs text-slate-500">
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span>Local Mode</span>
      </div>
    );
  }

  const host = window.location.hostname;
  const isNgrok = host.includes("ngrok");
  const origin = window.location.origin;

  const envApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const hasEnvApi = Boolean(envApiUrl && envApiUrl.trim().length > 0);

  // Determine current mode
  const mode = isNgrok ? "MOBILE / NGROK MODE" : "LOCAL MODE";

  // Determine frontend and backend URLs
  const frontendUrl = isNgrok ? origin : "http://localhost:3000";
  const backendUrl = hasEnvApi
    ? envApiUrl!.trim().replace(/\/+$/, "")
    : isNgrok
    ? `${origin}/api`
    : "http://127.0.0.1:8000";

  return (
    <div className="relative inline-block text-left text-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 rounded-full border border-[#e0d9f4] bg-white px-3 py-1.5 font-medium text-slate-700 shadow-sm transition hover:border-[#6247bf] hover:bg-[#faf9ff]"
        title="View connection & mobile access status"
      >
        <span
          className={`h-2 w-2 rounded-full ${
            isOnline ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
          }`}
        />
        <span className="font-semibold text-[#6247bf]">
          {isNgrok ? "Mobile (Ngrok)" : "Local Mode"}
        </span>
        <span className="text-[10px] text-slate-400">▾</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-50 mt-2 w-80 rounded-2xl border border-[#e0d9f4] bg-white p-4 text-xs shadow-xl" style={{ boxShadow: '0 16px 36px rgba(72, 52, 140, 0.12)' }}>
            <div className="flex items-center justify-between border-b border-[#f0ebfa] pb-2">
              <span className="font-bold uppercase tracking-wider text-[#6247bf]">
                {mode}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {isOnline ? "Connected" : "Offline"}
              </span>
            </div>

            <div className="mt-3 space-y-2.5">
              <div>
                <p className="font-semibold text-slate-500">Frontend:</p>
                <code className="mt-0.5 block truncate rounded-md bg-[#f6f4fd] px-2 py-1 font-mono text-[11px] text-[#4e3c99]">
                  {frontendUrl}
                </code>
              </div>

              <div>
                <p className="font-semibold text-slate-500">Backend API:</p>
                <code className="mt-0.5 block truncate rounded-md bg-[#f6f4fd] px-2 py-1 font-mono text-[11px] text-[#4e3c99]">
                  {backendUrl}
                </code>
              </div>

              {!isNgrok && (
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-2 text-[11px] text-slate-600">
                  <p className="font-medium text-slate-700">Mobile Access:</p>
                  <p className="mt-0.5">
                    {hasEnvApi
                      ? `Configured to ${envApiUrl}`
                      : "Mobile access is not configured."}
                  </p>
                </div>
              )}

              {isNgrok && (
                <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-2 text-[11px] text-emerald-800">
                  <p className="font-semibold">✓ Mobile Tunnel Active</p>
                  <p className="mt-0.5 text-emerald-700">
                    Requests are securely routed to your laptop backend.
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
