// api/leaderboard/_redis.js
const REDIS_URL = process.env.UPSTASH_REDIS_REST_URL;
const REDIS_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;

export async function redisZAdd(key, score, member) {
  if (!REDIS_URL || !REDIS_TOKEN) return;
  try {
    await fetch(`${REDIS_URL}/zadd/${encodeURIComponent(key)}/${score}/${encodeURIComponent(member)}`, {
      headers: { Authorization: `Bearer ${REDIS_TOKEN}` }
    });
  } catch (e) {
    console.error('redisZAdd error:', e);
  }
}

export async function redisZRevRange(key, start, stop, withScores = false) {
  if (!REDIS_URL || !REDIS_TOKEN) return [];
  try {
    const url = `${REDIS_URL}/zrevrange/${encodeURIComponent(key)}/${start}/${stop}${withScores ? '/WITHSCORES' : ''}`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${REDIS_TOKEN}` }
    });
    const data = await res.json();
    return data.result || [];
  } catch (e) {
    console.error('redisZRevRange error:', e);
    return [];
  }
}

// Store user metadata (name, streak) in a hash
export async function redisHSet(key, field, value) {
  if (!REDIS_URL || !REDIS_TOKEN) return;
  try {
    await fetch(`${REDIS_URL}/hset/${encodeURIComponent(key)}/${encodeURIComponent(field)}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${REDIS_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(value) // Value is serialized to JSON
    });
  } catch (e) {
    console.error('redisHSet error:', e);
  }
}

export async function redisHGetAll(key) {
  if (!REDIS_URL || !REDIS_TOKEN) return {};
  try {
    const res = await fetch(`${REDIS_URL}/hgetall/${encodeURIComponent(key)}`, {
      headers: { Authorization: `Bearer ${REDIS_TOKEN}` }
    });
    const data = await res.json();
    // Upstash returns an array [field1, val1, field2, val2]
    const result = {};
    if (data.result && Array.isArray(data.result)) {
      for (let i = 0; i < data.result.length; i += 2) {
        try {
          result[data.result[i]] = JSON.parse(data.result[i + 1]);
        } catch(e) {
          result[data.result[i]] = data.result[i + 1];
        }
      }
    }
    return result;
  } catch (e) {
    console.error('redisHGetAll error:', e);
    return {};
  }
}
