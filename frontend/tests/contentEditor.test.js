import assert from "node:assert/strict";
import test from "node:test";

import {
  buildEditorMarkdown,
  buildLineDiff,
  editorDraftEquals,
  normalizeEditorDraft,
  parseLocalEditorDraft,
} from "../src/utils/contentEditor.js";

test("editor draft normalization supports stable dirty checks", () => {
  const left = normalizeEditorDraft({ title: "A", content: "B" });
  const right = { ...left };
  assert.equal(editorDraftEquals(left, right), true);
  right.cta = "Mua ngay";
  assert.equal(editorDraftEquals(left, right), false);
});

test("local editor draft rejects invalid and incomplete snapshots", () => {
  assert.equal(parseLocalEditorDraft("bad json"), null);
  assert.equal(parseLocalEditorDraft('{"savedAt":1,"draft":{}}'), null);
  assert.equal(
    parseLocalEditorDraft('{"savedAt":2,"draft":{"title":"A","content":"B"}}')
      .draft.content,
    "B",
  );
});

test("line diff marks added, removed and changed lines", () => {
  const changed = buildLineDiff("a\nb", "a\nc\nnew");
  assert.deepEqual(changed.map((line) => line.kind), ["same", "changed", "added"]);
  assert.equal(buildLineDiff("a\nb", "a")[1].kind, "removed");
});

test("editor markdown preserves content, CTA and hashtags", () => {
  const markdown = buildEditorMarkdown({
    title: "Tiêu đề",
    content: "Nội dung",
    cta: "Đăng ký",
    hashtags: "#adgen",
  });
  assert.match(markdown, /# Tiêu đề/);
  assert.match(markdown, /## CTA/);
  assert.match(markdown, /#adgen/);
});
