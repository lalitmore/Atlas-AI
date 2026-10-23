import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
const require = createRequire(import.meta.url);
const { directionsUrl, fullRouteUrl, flightsUrl, hotelsUrl, foodUrl, placeUrl, atlasUrl } = require('../src/lib/links.ts');

test('PDF and UI route links preserve visit order and Unicode locations', () => {
  const route = new URL(fullRouteUrl(['東京', '京都', 'Osaka']));
  assert.equal(route.searchParams.get('origin'), '東京');
  assert.equal(route.searchParams.get('waypoints'), '京都');
  assert.equal(route.searchParams.get('destination'), 'Osaka');
  assert.equal(fullRouteUrl(['Tokyo']), directionsUrl(undefined, 'Tokyo'));
});

test('booking and place links preserve names, dietary needs, and party size', () => {
  assert.equal(new URL(hotelsUrl('Kyoto', 2)).searchParams.get('group_adults'), '2');
  assert.equal(new URL(flightsUrl('New York', 'Tokyo')).searchParams.get('q'), 'Flights to Tokyo from New York');
  assert.equal(new URL(foodUrl('Tokyo', 'vegetarian')).searchParams.get('query'), 'vegetarian restaurants in Tokyo');
  assert.equal(new URL(placeUrl('Café São Paulo 浅草', 'Tokyo')).searchParams.get('query'), 'Café São Paulo 浅草 Tokyo');
  assert.equal(atlasUrl(), 'https://atlasai-iota.vercel.app');
});
