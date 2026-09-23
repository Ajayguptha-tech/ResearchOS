import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.INTERNAL_BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const pathSegments = params?.path || [];
  const pathStr = pathSegments.join('/');
  const hasTrailingSlash = req.nextUrl.pathname.endsWith('/');
  const targetPath = hasTrailingSlash && !pathStr.endsWith('/') ? `${pathStr}/` : pathStr;
  const search = req.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/${targetPath}${search}`;

  const headers = new Headers();
  req.headers.forEach((val, key) => {
    const k = key.toLowerCase();
    if (!['host', 'connection', 'content-length'].includes(k)) {
      headers.set(key, val);
    }
  });
  headers.set('ngrok-skip-browser-warning', 'true');

  const method = req.method.toUpperCase();
  const body = ['GET', 'HEAD'].includes(method) ? undefined : await req.arrayBuffer();

  const response = await fetch(targetUrl, {
    method,
    headers,
    body,
    redirect: 'manual',
  });

  const responseHeaders = new Headers();
  response.headers.forEach((val, key) => {
    if (key.toLowerCase() === 'location') {
      try {
        const url = new URL(val);
        val = `${url.pathname}${url.search}`;
      } catch (_) {}
    }
    responseHeaders.set(key, val);
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const HEAD = handler;
export const OPTIONS = handler;
