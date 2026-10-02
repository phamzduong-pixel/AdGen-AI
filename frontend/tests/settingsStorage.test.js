import assert from "node:assert/strict";
import test from "node:test";

const values = new Map();
globalThis.localStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: (key) => values.delete(key),
};

const {
  DEFAULT_PREFERENCES,
  getPreferences,
  savePreferences,
} = await import("../src/utils/settingsStorage.js");

test("settings use safe defaults when local storage is empty", () => {
  values.clear();
  assert.deepEqual(getPreferences(), DEFAULT_PREFERENCES);
});

test("saved settings merge with defaults for forward compatibility", () => {
  values.clear();
  savePreferences({ theme: "dark", autoScroll: false });
  const preferences = getPreferences();
  assert.equal(preferences.theme, "dark");
  assert.equal(preferences.autoScroll, false);
  assert.equal(preferences.showMessageTime, true);
  assert.equal(preferences.defaultPlatform, "facebook");
});

test("invalid JSON falls back without exposing or crashing", () => {
  values.set("adgen_preferences", "{invalid");
  assert.deepEqual(getPreferences(), DEFAULT_PREFERENCES);
});
