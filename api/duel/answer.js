// api/duel/answer.js — POST /api/duel/answer
// Foydalanuvchi javobini saqlash

import { redisGet, redisSet } from './_utils.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { room_id, user_id, question_idx, answer, is_correct } = req.body;
  if (!room_id || !user_id || question_idx === undefined) {
    return res.status(400).json({ error: 'room_id, user_id, question_idx required' });
  }

  const room = await redisGet(`duel:room:${room_id}`);
  if (!room) return res.status(404).json({ error: 'Room not found' });

  const uid = String(user_id);
  if (!room.players[uid]) return res.status(403).json({ error: 'Not in this room' });

  // Javobni saqlash
  room.players[uid].answers[question_idx] = { answer, is_correct: Boolean(is_correct) };
  if (is_correct) {
    room.players[uid].score = (room.players[uid].score || 0) + 1;
  }

  // Hamma savollarga javob berganmi?
  const totalQ = (room.questions || []).length;
  const allPlayers = Object.keys(room.players);
  let allFinished = true;
  for (const pid of allPlayers) {
    if (Object.keys(room.players[pid].answers || {}).length < totalQ) {
      allFinished = false;
      break;
    }
  }
  if (allFinished) {
    room.status = 'finished';
  }

  await redisSet(`duel:room:${room_id}`, room, 600);

  return res.json({
    ok: true,
    my_score: room.players[uid].score,
    room_status: room.status
  });
}
