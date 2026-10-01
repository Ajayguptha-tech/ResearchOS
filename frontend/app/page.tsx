"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/workspace");
    } else {
      router.replace("/login");
    }
  }, [router]);

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
