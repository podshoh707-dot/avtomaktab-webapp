// api/duel/join.js — POST /api/duel/join
// Kod orqali xonaga qo'shilish

import { redisGet, redisSet } from './_utils.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { user_id, user_name, room_id } = req.body;
  if (!user_id || !room_id) return res.status(400).json({ error: 'user_id and room_id required' });

  const uid = String(user_id);
  const uname = user_name || "O'yinchi";
  const rid = String(room_id).toUpperCase();

  const room = await redisGet(`duel:room:${rid}`);
  if (!room) return res.status(404).json({ error: 'Xona topilmadi', uz: 'Bunday kod bilan xona topilmadi.' });
  if (room.status !== 'waiting') return res.status(409).json({ error: 'Room not waiting', uz: 'Xona allaqachon to\'lgan yoki tugagan.' });
  if (room.creator_id === uid) return res.status(400).json({ error: 'Cannot join own room', uz: 'O\'z xonangizga kira olmaysiz.' });

  room.status = 'active';
  room.players[uid] = {
    name: uname,
    score: 0,
    answers: {},
    joined_at: Date.now()
  };
  room.started_at = Date.now();

  await redisSet(`duel:room:${rid}`, room, 600);

  const creatorName = room.players[room.creator_id]?.name || 'Raqib';

  return res.json({
    status: 'active',
    room_id: rid,
    questions: room.questions,
    opponent_name: creatorName
  });
}
