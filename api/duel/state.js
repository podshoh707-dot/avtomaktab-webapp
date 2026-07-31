// api/duel/state.js — GET /api/duel/state?room_id=...&user_id=...
// Xona holati so'rovi (polling uchun)

import { redisGet } from './_utils.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { room_id, user_id } = req.query;
  if (!room_id || !user_id) return res.status(400).json({ error: 'room_id and user_id required' });

  const room = await redisGet(`duel:room:${room_id}`);
  if (!room) return res.status(404).json({ error: 'Room not found' });

  const players = room.players || {};
  const playerIds = Object.keys(players);
  const myData = players[user_id] || {};
  const oppId = playerIds.find(id => id !== user_id);
  const oppData = oppId ? players[oppId] : null;

  return res.json({
    status: room.status,
    room_id: room.room_id,
    my_score: myData.score || 0,
    opp_score: oppData ? (oppData.score || 0) : 0,
    opp_name: oppData ? oppData.name : null,
    player_count: playerIds.length,
    questions: room.questions || [],
    answers: myData.answers || {}
  });
}
