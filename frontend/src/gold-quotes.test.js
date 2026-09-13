const assert = require("node:assert/strict");
const test = require("node:test");

const { fetchGoldQuotes, normalizeGoldApiData } = require("./gold-quotes");

test("gold quote fetch keeps API keys out of the returned payload", async () => {
  const secret = "test-gold-key";
  const quotes = await fetchGoldQuotes({
    goldApiKey: secret,
    metalpriceApiKey: "",
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        price: 2400,
        price_gram_24k: 77,
        currency: "USD",
        timestamp: 1,
      }),
    }),
  });

  assert.equal(quotes.source, "goldapi");
  assert.equal(quotes.price, 2400);
  assert.equal(JSON.stringify(quotes).includes(secret), false);
  assert.deepEqual(normalizeGoldApiData({ price: 2400, currency: "USD" }).source, "goldapi");
});
