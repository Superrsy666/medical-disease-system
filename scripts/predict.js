(async () => {
  try {
    const res = await fetch('http://localhost:8088/api/prediction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms: '发热 咳嗽 头痛' }),
    });
    const json = await res.json();
    console.log(JSON.stringify(json, null, 2));
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
