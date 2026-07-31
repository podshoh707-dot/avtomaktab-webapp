// api/duel/_utils.js — Upstash Redis REST API + helpers

const REDIS_URL = process.env.UPSTASH_REDIS_REST_URL;
const REDIS_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;

// ── Redis helpers ──────────────────────────────────────────────

export async function redisGet(key) {
  if (!REDIS_URL || !REDIS_TOKEN) {
    console.error('Upstash Redis env vars not set!');
    return null;
  }
  try {
    const res = await fetch(`${REDIS_URL}/get/${encodeURIComponent(key)}`, {
      headers: { Authorization: `Bearer ${REDIS_TOKEN}` }
    });
    const data = await res.json();
    return data.result ? JSON.parse(data.result) : null;
  } catch (e) {
    console.error('redisGet error:', e);
    return null;
  }
}

export async function redisSet(key, value, exSeconds = 1800) {
  if (!REDIS_URL || !REDIS_TOKEN) return;
  try {
    await fetch(`${REDIS_URL}/set/${encodeURIComponent(key)}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${REDIS_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify([JSON.stringify(value), 'EX', exSeconds])
    });
  } catch (e) {
    console.error('redisSet error:', e);
  }
}

export async function redisDel(key) {
  if (!REDIS_URL || !REDIS_TOKEN) return;
  try {
    await fetch(`${REDIS_URL}/del/${encodeURIComponent(key)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${REDIS_TOKEN}` }
    });
  } catch (e) {
    console.error('redisDel error:', e);
  }
}

// ── Helpers ────────────────────────────────────────────────────

export function randomId(len = 8) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let id = '';
  for (let i = 0; i < len; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

// Savollarni questions.json dan olish (Vercel static hosting da bu fayl mavjud)
// Node.js serverless context da fs bilan o'qiymiz
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

let _cachedQuestions = null;

function loadQuestions() {
  if (_cachedQuestions) return _cachedQuestions;
  try {
    const __dirname = dirname(fileURLToPath(import.meta.url));
    // questions.json webapp root da
    const qPath = join(__dirname, '..', '..', 'questions.json');
    const raw = readFileSync(qPath, 'utf-8');
    _cachedQuestions = JSON.parse(raw);
    return _cachedQuestions;
  } catch (e) {
    console.error('Failed to load questions.json:', e.message);
    return [];
  }
}

export function pickQuestions(count = 10) {
  const all = loadQuestions();
  if (!all || all.length === 0) return [];
  // Tasodifiy savollar
  const shuffled = [...all].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, Math.min(count, shuffled.length)).map(q => ({
    id: q.id,
    text: q.text,
    image_url: q.image_url || null,
    option_a: q.option_a,
    option_b: q.option_b,
    option_c: q.option_c,
    option_d: q.option_d,
    correct_option: q.correct_option,
    options: q.options || []
  }));
}
