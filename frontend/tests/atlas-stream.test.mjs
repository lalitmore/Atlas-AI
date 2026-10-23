import assert from 'node:assert/strict';
import { test, mock } from 'node:test';
import { createRequire } from 'node:module';
const { streamPlan } = createRequire(import.meta.url)('../src/lib/atlas.ts');

test('preserves stage and stable error details across split CRLF SSE frames', async () => {
  const text = 'event: stage\r\ndata: {"name":"intake","label":"Understanding"}\r\n\r\n'
    + 'event: error\r\ndata: {"code":"NETWORK_ERROR","message":"Check your connection.","stage":"intake"}\r\n\r\n';
  const bytes = new TextEncoder().encode(text);
  const fetch = mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += 7) controller.enqueue(bytes.slice(i, i + 7));
      controller.close();
    },
  })));
  try {
    const events = await Array.fromAsync(streamPlan('Japan'));
    assert.deepEqual(events, [
      { type: 'stage', name: 'intake', label: 'Understanding' },
      { type: 'error', code: 'NETWORK_ERROR', message: 'Check your connection.', stage: 'intake' },
    ]);
  } finally { fetch.mock.restore(); }
});

test('reads the same friendly error shape from pre-stream HTTP failures', async () => {
  const fetch = mock.method(globalThis, 'fetch', async () => Response.json({
    detail: { code: 'RATE_LIMITED', message: 'Try again later.', stage: null },
  }, { status: 429 }));
  try {
    assert.deepEqual(await Array.fromAsync(streamPlan('Japan')), [
      { type: 'error', code: 'RATE_LIMITED', message: 'Try again later.', stage: null },
    ]);
  } finally { fetch.mock.restore(); }
});

test('does not treat a truncated stream as a completed plan', async () => {
  const fetch = mock.method(globalThis, 'fetch', async () => new Response(''));
  try {
    const events = await Array.fromAsync(streamPlan('Japan'));
    assert.equal(events.at(-1).code, 'INCOMPLETE_STREAM');
  } finally { fetch.mock.restore(); }
});

for (const terminal of ['complete', 'error']) {
  test(`stops reading and closes the transport after ${terminal}`, { timeout: 1000 }, async () => {
    let cancelled = false;
    const payload = terminal === 'complete' ? { itinerary: { destination: 'Japan' } }
      : { code: 'AI_CONNECTION_ERROR', message: 'Check your connection.', stage: 'intake' };
    const fetch = mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(`event: ${terminal}\ndata: ${JSON.stringify(payload)}\n\n`));
        // Intentionally leave open: the terminal event must be enough to finish.
      },
      cancel() { cancelled = true; },
    })));
    try {
      const events = await Array.fromAsync(streamPlan('Japan'));
      assert.equal(events.length, 1);
      assert.equal(events[0].type, terminal);
      assert.equal(cancelled, true);
    } finally { fetch.mock.restore(); }
  });
}
