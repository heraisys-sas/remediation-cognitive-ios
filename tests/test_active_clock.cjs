const test = require('node:test');
const assert = require('node:assert/strict');
const ActiveClock = require('../mobile/ios/pilot/active-clock.js');

test('une longue interruption ne devient pas du temps de réponse', () => {
  let now = 0;
  const clock = new ActiveClock(() => now);
  now = 1500;
  clock.pause();
  now += 2 * 86400000;
  clock.pause();
  assert.equal(clock.elapsed(), 1500);
  clock.resume();
  now += 500;
  assert.equal(clock.elapsed(), 2000);
});

test('une nouvelle question préparée pendant la pause attend la reprise', () => {
  let now = 0;
  const clock = new ActiveClock(() => now);
  clock.pause();
  clock.reset(true);
  now += 600000;
  assert.equal(clock.elapsed(), 0);
  clock.resume();
  now += 700;
  assert.equal(clock.elapsed(), 700);
});
