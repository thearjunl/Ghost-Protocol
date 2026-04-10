/**
 * Server-side API proxy for GhostProtocol.
 *
 * Forwards requests to the backend API, injecting the API key
 * server-side so it is never exposed to the browser.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.GHOSTPROTOCOL_API_KEY || "";

async function proxyRequest(request: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `${BACKEND_URL}/${path}`;

  const headers: Record<string, string> = {
    "Content-Type": request.headers.get("content-type") || "application/json",
  };

  // Inject API key server-side — never exposed to browser
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  // Forward request ID if present
  const requestId = request.headers.get("x-request-id");
  if (requestId) {
    headers["X-Request-ID"] = requestId;
  }

  try {
    const fetchOpts: RequestInit = {
      method: request.method,
      headers,
    };

    // Forward body for POST/PUT/PATCH
    if (["POST", "PUT", "PATCH"].includes(request.method)) {
      fetchOpts.body = await request.text();
    }

    const response = await fetch(url, fetchOpts);
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
        ...(response.headers.get("x-request-id")
          ? { "X-Request-ID": response.headers.get("x-request-id")! }
          : {}),
      },
    });
  } catch (error) {
    console.error(`Proxy error for ${url}:`, error);
    return NextResponse.json(
      { detail: "Backend service unavailable" },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
