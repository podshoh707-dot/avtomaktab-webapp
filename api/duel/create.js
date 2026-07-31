// api/duel/create.js — POST /api/duel/create
// Yangi duel xonasi yaratish yoki mavjud kutayotgan xonaga qo'shilish (matchmaking)

import { redisGet, redisSet, redisDel, randomId, pickQuestions } from './_utils.js';

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { user_id, user_name } = req.body;
  if (!user_id) return res.status(400).json({ error: 'user_id required' });

  const uid = String(user_id);
  const uname = user_name || "O'yinchi";

  // Kutayotgan xona bormi?
  const waitingRoomId = await redisGet('duel:waiting');

  if (waitingRoomId) {
    // Xona bor — qo'shilish
    const room = await redisGet(`duel:room:${waitingRoomId}`);
    if (room && room.status === 'waiting' && room.creator_id !== uid) {
      // Raqib sifatida qo'shilish
      room.status = 'active';
      room.players[uid] = {
        name: uname,
        score: 0,
        answers: {},
        joined_at: Date.now()
      };
      room.started_at = Date.now();
      await redisSet(`duel:room:${waitingRoomId}`, room, 600);
      await redisDel('duel:waiting');

      return res.json({
        status: 'active',
        room_id: waitingRoomId,
        questions: room.questions,
        opponent_name: room.players[room.creator_id].name
      });
    }
    // Xona yaroqsiz — tozalab yangi yaratamiz
    await redisDel('duel:waiting');
  }

  // Yangi xona yaratish
  const roomId = randomId(8);
  const questions = pickQuestions(10);

  const room = {
    room_id: roomId,
    status: 'waiting',
    creator_id: uid,
    created_at: Date.now(),
    questions,
    players: {
      [uid]: {
        name: uname,
        score: 0,
        answers: {},
        joined_at: Date.now()
      }
    }
  };

  await redisSet(`duel:room:${roomId}`, room, 600);
  await redisSet('duel:waiting', roomId, 300); // 5 daqiqa kutish

  return res.json({
    status: 'waiting',
    room_id: roomId,
    questions
  });
}
