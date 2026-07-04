/**
 * client.js — All API calls to the FastAPI backend.
 *
 * In development: Vite proxies /api/* → http://localhost:8000/*
 * In production:  Set VITE_API_URL env var to your Railway backend URL
 */

const BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
  : '/api';

/**
 * Ask a question against the ingested documents.
 * @param {string} question
 * @param {string} sessionId
 * @returns {Promise<{answer: string, sources: Array}>}
 */
export async function askQuestion(question, sessionId = 'default') {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${res.status}`);
  }

  return res.json();
}

/**
 * Upload one or more PDF files to be ingested.
 * @param {File[]} files
 * @returns {Promise<{status: string, files_ingested: number, chunks_added: number}>}
 */
export async function uploadFiles(files) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Check API health and get vectorstore stats.
 * @returns {Promise<{status: string, vectorstore_chunks: number}>}
 */
export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('API offline');
  return res.json();
}
