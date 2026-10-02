import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTemplateBrief,
  filterAdTemplates,
} from "../src/utils/adTemplate.js";

const templates = [
  {
    id: 1,
    title: "Facebook ra mắt",
    description: "Giới thiệu sản phẩm mới",
    platform: "facebook",
    category: "Ra mắt sản phẩm",
    default_tone: "Thuyết phục",
    default_length: "Trung bình",
    suggested_cta: "Khám phá ngay",
    is_popular: true,
    is_favorite: false,
    is_owner: false,
  },
  {
    id: 2,
    title: "Email ưu đãi",
    description: "Khuyến mãi cho khách hàng cũ",
    platform: "email",
    category: "Quảng cáo khuyến mãi",
    default_tone: "Gần gũi",
    default_length: "Ngắn",
    suggested_cta: "Nhận ưu đãi",
    is_popular: false,
    is_favorite: true,
    is_owner: true,
  },
];

test("template becomes an editable ad brief without sending AI", () => {
  const brief = buildTemplateBrief(templates[0]);
  assert.equal(brief.platform, "facebook");
  assert.equal(brief.tone, "Thuyết phục");
  assert.equal(brief.length, "Trung bình");
  assert.equal(brief.cta, "Khám phá ngay");
  assert.equal(brief.objective, "Nhận diện thương hiệu");
});

test("template search and platform/category filters combine", () => {
  const result = filterAdTemplates(templates, {
    query: "khuyến mãi",
    platform: "email",
    category: "Quảng cáo khuyến mãi",
    scope: "all",
  });
  assert.deepEqual(result.map((item) => item.id), [2]);
});

test("favorite and custom scopes remain user-specific", () => {
  const favorite = filterAdTemplates(templates, {
    query: "",
    platform: "",
    category: "",
    scope: "favorites",
  });
  const custom = filterAdTemplates(templates, {
    query: "",
    platform: "",
    category: "",
    scope: "custom",
  });
  assert.deepEqual(favorite.map((item) => item.id), [2]);
  assert.deepEqual(custom.map((item) => item.id), [2]);
});
