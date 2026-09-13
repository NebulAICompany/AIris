const assert = require("node:assert/strict");
const test = require("node:test");

const { isAllowedExternalUrl } = require("./security");

test("external URL validation only permits credential-free HTTP URLs", () => {
  assert.equal(isAllowedExternalUrl("https://example.com/report"), true);
  assert.equal(isAllowedExternalUrl("http://example.com/report"), true);
  assert.equal(isAllowedExternalUrl("javascript:alert(1)"), false);
  assert.equal(isAllowedExternalUrl("file:///C:/Windows/win.ini"), false);
  assert.equal(isAllowedExternalUrl("https://user:pass@example.com"), false);
});
