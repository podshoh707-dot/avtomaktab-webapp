// api/leaderboard/top.js — GET /api/leaderboard/top
// Fetch top 100 players from the leaderboard

import { redisZRevRange, redisHGetAll } from './_redis.js';

export default async function handler(req, res) {
  // CORS setup
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // Get top 100 users by score (with scores)
    // Upstash returns [member1, score1, member2, score2, ...]
    const topData = await redisZRevRange('avp_leaderboard', 0, 99, true);
    
    // Get all user metadata (names, streaks)
    const usersMeta = await redisHGetAll('avp_users_meta');
    
    const leaderboard = [];
    for (let i = 0; i < topData.length; i += 2) {
      const userId = topData[i];
      const score = topData[i+1];
      const meta = usersMeta[userId] || { name: 'Foydalanuvchi', streak: 0 };
      
      leaderboard.push({
        rank: (i / 2) + 1,
        userId,
        name: meta.name || 'Foydalanuvchi',
        score: parseInt(score),
        streak: meta.streak || 0
      });
    }

    return res.status(200).json({ leaderboard });
  } catch (e) {
    console.error('Leaderboard top fetch error:', e);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
