import { redisGet, redisSet } from './_utils.js';

export default async function handler(req, res) {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const { room_id, user_id, emoji } = req.body;
  if (!room_id || !user_id || !emoji) {
    return res.status(400).json({ error: 'room_id, user_id and emoji are required' });
  }

  try {
    const room = await redisGet(`duel:room:${room_id}`);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }

    // Saqlash: kim qanday emoji jo'natgani haqida ma'lumot
    // Biz eng so'nggi emojini saqlaymiz.
    // Client tomonidan har 2 soniyada poll qilinganda buni o'qib animatsiya chiqariladi
    room.last_reaction = {
      user_id,
      emoji,
      ts: Date.now()
    };
    
    // Qayta saqlash
    await redisSet(`duel:room:${room_id}`, room);
    
    return res.status(200).json({ success: true, reaction: room.last_reaction });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
}
