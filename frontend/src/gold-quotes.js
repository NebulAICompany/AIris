const OUNCE_TO_GRAM = 31.1034768;
const GOLD_FETCH_TIMEOUT_MS = 10000;

function toNumber(value) {
  return value === null || value === undefined || value === ""
    ? null
    : Number(value);
}

function normalizeGoldApiData(data) {
  const gramUsd = toNumber(data.price_gram_24k);
  const ounceUsd =
    toNumber(data.price) ||
    toNumber(data.ask) ||
    (gramUsd ? gramUsd * OUNCE_TO_GRAM : null);

  if (!ounceUsd) {
    throw new Error("GoldAPI response missing price");
  }

  return {
    price: ounceUsd,
    ounceUsd,
    gramUsd: gramUsd ?? ounceUsd / OUNCE_TO_GRAM,
    open_price: toNumber(data.open_price),
    low_price: toNumber(data.low_price),
    high_price: toNumber(data.high_price),
    timestamp: data.timestamp || Date.now(),
    currency: data.currency || "USD",
    source: "goldapi",
    isOffline: false,
  };
}

function normalizeMetalpriceData(data) {
  if (!data.success) {
    throw new Error("MetalpriceAPI response not successful");
  }

  const xauRate = toNumber(data.rates && data.rates.XAU);
  if (!xauRate) {
    throw new Error("MetalpriceAPI response missing XAU rate");
  }

  const ounceUsd = 1.0 / xauRate;
  return {
    price: ounceUsd,
    ounceUsd,
    gramUsd: ounceUsd / OUNCE_TO_GRAM,
    timestamp: Date.now(),
    currency: "USD",
    source: "metalpriceapi",
    isOffline: false,
  };
}

async function requestJson(url, headers, fetchImpl) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), GOLD_FETCH_TIMEOUT_MS);
  try {
    const response = await fetchImpl(url, {
      headers,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timeout");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchGoldQuotes({
  goldApiKey,
  metalpriceApiKey,
  fetchImpl = globalThis.fetch,
}) {
  const errors = [];

  if (goldApiKey) {
    try {
      const data = await requestJson(
        "https://www.goldapi.io/api/XAU/USD",
        {
          Accept: "application/json",
          "Cache-Control": "no-cache",
          "X-Access-Token": goldApiKey,
          "Content-Type": "application/json",
        },
        fetchImpl
      );
      return normalizeGoldApiData(data);
    } catch (error) {
      errors.push(error);
    }
  }

  if (metalpriceApiKey) {
    try {
      const data = await requestJson(
        `https://api.metalpriceapi.com/v1/latest?api_key=${encodeURIComponent(
          metalpriceApiKey
        )}&base=USD&currencies=XAU`,
        {
          Accept: "application/json",
          "Cache-Control": "no-cache",
        },
        fetchImpl
      );
      return normalizeMetalpriceData(data);
    } catch (error) {
      errors.push(error);
    }
  }

  const error = new Error(
    errors.map((item) => item.message).join("; ") ||
      "No gold API keys configured"
  );
  error.code =
    goldApiKey || metalpriceApiKey ? "GOLD_FETCH_FAILED" : "GOLD_KEYS_MISSING";
  throw error;
}

module.exports = {
  fetchGoldQuotes,
  normalizeGoldApiData,
  normalizeMetalpriceData,
};
