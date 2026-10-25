(async () => {
  try {
    const res = await fetch('http://localhost:8088/api/prediction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms: '发热 咳嗽 头痛' }),
    });
    const json = await res.json();
    if (!json || !json.data) {
      console.log(JSON.stringify(json, null, 2));
      return;
    }
    const summary = json.data.map(item => ({
      matchedDisease: item.matchedDisease,
      confidence: item.confidence,
      advice: item.advice && item.advice.length > 120 ? item.advice.slice(0,120) + '...' : item.advice
    }));
    console.log(JSON.stringify(summary, null, 2));
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
