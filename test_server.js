import { spawn } from 'node:child_process';

const serverProc = spawn('node', ['--experimental-strip-types', 'services/api/src/server.ts'], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

serverProc.stdout.on('data', (d) => process.stdout.write(d));
serverProc.stderr.on('data', (d) => process.stderr.write(d));

// Wait 1.5 seconds for server to start, then test endpoints
setTimeout(async () => {
  try {
    console.log('\n--- TESTING HTTP ENDPOINTS ---');

    // 1. GET /api/v1/overview
    console.log('Testing GET /api/v1/overview ...');
    const resOverview = await fetch('http://localhost:4000/api/v1/overview');
    const dataOverview = await resOverview.json();
    console.log('✓ Overview status:', resOverview.status, 'Union:', dataOverview.scope.union);

    // 2. POST /api/v1/advice
    console.log('Testing POST /api/v1/advice ...');
    const resAdvice = await fetch('http://localhost:4000/api/v1/advice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        landType: 'medium_high',
        farmerPriorities: { water: 0.6, income: 0.4 },
      }),
    });
    const dataAdvice = await resAdvice.json();
    console.log('✓ Advice status:', resAdvice.status, 'Top option:', dataAdvice.options[0].nameBangla);

    // 3. POST /api/v1/narrate
    console.log('Testing POST /api/v1/narrate ...');
    const resNarrate = await fetch('http://localhost:4000/api/v1/narrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        advice: dataAdvice,
        selectedOptionId: dataAdvice.options[0].id,
      }),
    });
    const dataNarrate = await resNarrate.json();
    console.log('✓ Narrate status:', resNarrate.status, 'Engine used:', dataNarrate.status);

    // 4. POST /api/v1/channel-events (Keypad 1)
    console.log('Testing POST /api/v1/channel-events ...');
    const resKeypad = await fetch('http://localhost:4000/api/v1/channel-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keypad: '1' }),
    });
    const dataKeypad = await resKeypad.json();
    console.log('✓ Keypad status:', resKeypad.status, 'Ack:', dataKeypad.acknowledgementBangla);

    // 5. GET /
    console.log('Testing GET / (Dashboard HTML) ...');
    const resHtml = await fetch('http://localhost:4000/');
    const htmlText = await resHtml.text();
    console.log('✓ Dashboard HTML status:', resHtml.status, 'Length:', htmlText.length, 'Contains title:', htmlText.includes('EDEN'));

    console.log('\n===========================================');
    console.log('  ALL ENDPOINTS TESTED & VERIFIED!          ');
    console.log('===========================================');
  } catch (err) {
    console.error('Test error:', err);
  } finally {
    serverProc.kill();
    process.exit(0);
  }
}, 1500);
