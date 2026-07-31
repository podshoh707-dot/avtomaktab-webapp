import { redisGet, redisSet, randomId, pickQuestions } from './_utils.js';

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

  const { room_id, user_id } = req.body;
  if (!room_id || !user_id) {
    return res.status(400).json({ error: 'room_id and user_id are required' });
  }

  try {
    const room = await redisGet(`duel:room:${room_id}`);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }

    if (!room.rematch_requested) {
      room.rematch_requested = {};
    }
    room.rematch_requested[user_id] = true;

    // Check if both agreed
    const p1 = room.player1.id;
    const p2 = room.player2 ? room.player2.id : null;
    
    if (p1 && p2 && room.rematch_requested[p1] && room.rematch_requested[p2]) {
      // Both agreed -> Create a new room
      const newRoomId = randomId(6);
      const newRoom = {
        id: newRoomId,
        status: 'playing', // since both already agreed, start directly!
        player1: room.player1,
        player2: room.player2,
        questions: pickQuestions(10),
        p1_answers: [],
        p2_answers: [],
        p1_score: 0,
        p2_score: 0,
        created_at: Date.now(),
        // Keep tracking the original creator
        creator_id: room.creator_id
      };
      
      // Save new room
      await redisSet(`duel:room:${newRoomId}`, newRoom);
      
      // Notify old room
      room.next_room_id = newRoomId;
    }
    
    // Save old room
    await redisSet(`duel:room:${room_id}`, room);
    
    return res.status(200).json({ success: true, next_room_id: room.next_room_id });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
}
