// api/leaderboard/update.js — POST /api/leaderboard/update
// Update user score and streak in the global leaderboard

import { redisZAdd, redisHSet } from './_redis.js';

export default async function handler(req, res) {
  // CORS setup
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { userId, name, score, streak } = req.body;
    if (!userId || score === undefined) {
      return res.status(400).json({ error: 'Missing userId or score' });
    }

    // Update global sorted set (Leaderboard) with score
    await redisZAdd('avp_leaderboard', score, userId);

    // Save user metadata (name and streak) in a hash
    await redisHSet('avp_users_meta', userId, { name: name || 'Anonim', streak: streak || 0 });

    return res.status(200).json({ success: true });
  } catch (e) {
    console.error('Leaderboard update error:', e);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
