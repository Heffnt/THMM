import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

async function loadPresentationApi() {
  try {
    return await import("@oai/artifact-tool");
  } catch {
    const fallback = path.join(
      homedir(),
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "node",
      "node_modules",
      "@oai",
      "artifact-tool",
      "dist",
      "artifact_tool.mjs",
    );
    if (!existsSync(fallback)) {
      throw new Error("Could not load @oai/artifact-tool. Run this from Cursor/Codex or install the package.");
    }
    return await import(pathToFileURL(fallback).href);
  }
}

const { Presentation, PresentationFile } = await loadPresentationApi();

const W = 1280;
const H = 720;
const I = 96;
const inch = (n) => n * I;

const BG = "#FAF8F3";
const INK = "#1A1A1A";
const ACCENT = "#C4422E";
const ACCENT2 = "#2E6EA0";
const DIM = "#6B6B6B";
const LIGHT = "#E6E2D8";
const CODE_BG = "#F1ECE0";
const HIGHLIGHT = "#FFE89C";
const DARK_BG = "#141414";
const WHITE = "#FFFFFF";
const TRANSPARENT = "#FFFFFF00";

const SANS = "Aptos";
const SERIF = "Georgia";
const MONO = "Consolas";

const ppt = Presentation.create({ slideSize: { width: W, height: H } });

function slide(bg = BG) {
  const s = ppt.slides.add();
  s.background.fill = bg;
  return s;
}

function stroke(color = INK, width = 1) {
  if (!color || width <= 0) return { style: "solid", fill: TRANSPARENT, width: 0 };
  return { style: "solid", fill: color, width };
}

function addRect(s, x, y, w, h, { fill = TRANSPARENT, line = INK, lineWidth = 1, rounded = false } = {}) {
  const sh = s.shapes.add({
    geometry: rounded ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: stroke(line, lineWidth),
  });
  return sh;
}

function addText(
  s,
  text,
  x,
  y,
  w,
  h,
  { size = 18, bold = false, italic = false, color = INK, align = "left", valign = "top", font = SANS } = {},
) {
  const sh = addRect(s, x, y, w, h, { fill: TRANSPARENT, line: null, lineWidth: 0 });
  sh.text = String(text).includes("\n") ? String(text).split("\n") : String(text);
  sh.text.fontSize = size;
  sh.text.bold = bold;
  sh.text.italic = italic;
  sh.text.color = color;
  sh.text.typeface = font;
  sh.text.alignment = align;
  sh.text.verticalAlignment = valign;
  sh.text.insets = { left: 0, right: 0, top: 0, bottom: 0 };
  sh.text.autoFit = "shrinkText";
  return sh;
}

function addLine(s, x1, y1, x2, y2, { color = INK, width = 2 } = {}) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  if (!len) return null;
  const th = Math.max(1, width * 1.25);
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  return s.shapes.add({
    geometry: "rect",
    position: { left: (x1 + x2) / 2 - len / 2, top: (y1 + y2) / 2 - th / 2, width: len, height: th, rotation: angle },
    fill: color,
    line: stroke(null, 0),
  });
}

function addArrow(s, x1, y1, x2, y2, { color = INK, width = 2 } = {}) {
  addLine(s, x1, y1, x2, y2, { color, width });
  const dx = x2 - x1;
  const dy = y2 - y1;
  if (!dx && !dy) return;
  const size = 16 + width * 2;
  const head = s.shapes.add({
    geometry: "triangle",
    position: { left: x2 - size / 2, top: y2 - size / 2, width: size, height: size, rotation: (Math.atan2(dy, dx) * 180) / Math.PI + 90 },
    fill: color,
    line: stroke(null, 0),
  });
  return head;
}

function slideTitle(s, text, color = DIM) {
  addText(s, text.toUpperCase(), inch(0.6), inch(0.45), inch(12.0), inch(0.4), {
    size: 14,
    bold: true,
    color,
    font: SANS,
  });
}

function slideCaption(s, text, { color = DIM } = {}) {
  addText(s, text, inch(0.6), inch(6.7), inch(12.1), inch(0.5), {
    size: 18,
    italic: true,
    color,
    align: "center",
    font: SANS,
  });
}

function addCode(s, code, x, y, w, h, { size = 20, highlights = [] } = {}) {
  addRect(s, x, y, w, h, { fill: CODE_BG, line: null, lineWidth: 0 });
  const lines = String(code).split("\n");
  const top = y + inch(0.12);
  const left = x + inch(0.18);
  const lineH = Math.max(size * 1.28, 17);
  lines.forEach((line, i) => {
    addText(s, line || " ", left, top + i * lineH, w - inch(0.36), lineH + 4, {
      size,
      bold: highlights.includes(i),
      color: highlights.includes(i) ? ACCENT : INK,
      font: MONO,
    });
  });
}

function addAccumulatorBox(s, x, y, value, label = "acc") {
  addRect(s, x, y, inch(1.2), inch(0.7), { fill: WHITE, line: INK, lineWidth: 1.5 });
  addText(s, value, x, y, inch(1.2), inch(0.7), { size: 22, bold: true, font: MONO, align: "center", valign: "middle" });
  addText(s, label, x, y + inch(0.75), inch(1.2), inch(0.3), { size: 11, color: DIM, align: "center" });
}

function treeNode(s, label, cx, cy, { w = inch(1.0), h = inch(0.7), fill = WHITE } = {}) {
  addRect(s, cx - w / 2, cy, w, h, { fill, line: INK, lineWidth: 1.5, rounded: true });
  addText(s, label, cx - w / 2, cy, w, h, { size: 24, bold: true, font: MONO, align: "center", valign: "middle" });
  return { cx, top: cy, bottom: cy + h };
}

function treeEdge(s, parent, child) {
  addLine(s, parent.cx, parent.bottom, child.cx, child.top, { color: DIM, width: 1.5 });
}

function drawStack(s, lit = new Set()) {
  const layers = [
    ["caesar.thcc", "source", ACCENT],
    ["AST", "tree", ACCENT2],
    [".asm  /  .hex", "machine code", ACCENT],
    ["THMM", "hardware", ACCENT2],
    ["RAM cells", "result", ACCENT],
  ];
  const arrows = ["parse", "codegen + link", "load", "run", "read"];
  const x = inch(3.2);
  const top = inch(1.4);
  const w = inch(7.0);
  const h = inch(0.85);
  const gap = inch(0.2);
  layers.forEach(([name, sub, col], i) => {
    const y = top + i * (h + gap);
    const on = lit.has(i);
    addRect(s, x, y, w, h, { fill: on ? col : WHITE, line: on ? null : INK, lineWidth: 1.5, rounded: true });
    addText(s, name, x + inch(0.4), y, inch(3.5), h, { size: 22, bold: true, color: on ? WHITE : INK, font: MONO, valign: "middle" });
    addText(s, sub, x + inch(3.5), y, inch(3.0), h, { size: 14, italic: true, color: on ? WHITE : DIM, align: "right", valign: "middle" });
    if (i < layers.length - 1) {
      addText(s, arrows[i], x + w + inch(0.2), y + h - inch(0.05), inch(2.4), inch(0.3), { size: 12, italic: true, color: DIM });
      addArrow(s, x + w / 2, y + h, x + w / 2, y + h + gap, { color: DIM, width: 2 });
    }
  });
}

function pythagorasTree(s, cx = W / 2, rootY = inch(3.0), half = inch(2.6)) {
  const root = treeNode(s, "+", cx, rootY, { fill: HIGHLIGHT });
  const mulL = treeNode(s, "x", cx - half, rootY + inch(1.3));
  const mulR = treeNode(s, "x", cx + half, rootY + inch(1.3));
  const leafY = rootY + inch(2.6);
  const off = inch(1.0);
  const a1 = treeNode(s, "a", cx - half - off, leafY, { fill: LIGHT });
  const a2 = treeNode(s, "a", cx - half + off, leafY, { fill: LIGHT });
  const b1 = treeNode(s, "b", cx + half - off, leafY, { fill: LIGHT });
  const b2 = treeNode(s, "b", cx + half + off, leafY, { fill: LIGHT });
  [mulL, mulR].forEach((n) => treeEdge(s, root, n));
  [a1, a2].forEach((n) => treeEdge(s, mulL, n));
  [b1, b2].forEach((n) => treeEdge(s, mulR, n));
}

// 1
{
  const s = slide();
  addText(s, "2 + 2 = ?", 0, inch(2.4), W, inch(2.5), { size: 180, bold: true, font: SERIF, align: "center" });
  addText(s, "ALU", 0, inch(5.3), W, inch(0.6), { size: 28, bold: true, color: ACCENT, align: "center" });
  addText(s, "(arithmetic logic unit)", 0, inch(5.85), W, inch(0.4), { size: 16, italic: true, color: DIM, align: "center" });
}

// 2
{
  const s = slide();
  slideTitle(s, "ALU + Memory");
  addText(s, "(5 + 3)  x  (7 + 2)", 0, inch(1.2), W, inch(1.0), { size: 56, bold: true, font: SERIF, align: "center" });
  const x = inch(2.8), y = inch(3.0), cw = inch(3.0), ch = inch(2.8);
  addRect(s, x, y, cw, ch, { fill: LIGHT, line: INK, lineWidth: 1.5, rounded: true });
  addText(s, "calculator", x, y + inch(0.2), cw, inch(0.4), { size: 14, bold: true, color: DIM, align: "center" });
  [["M+", 0.3], ["MR", 1.7]].forEach(([t, ox]) => {
    addRect(s, x + inch(ox), y + inch(0.9), inch(1.0), inch(0.6), { fill: ACCENT, line: null, rounded: true });
    addText(s, t, x + inch(ox), y + inch(0.9), inch(1.0), inch(0.6), { size: 20, bold: true, color: WHITE, align: "center", valign: "middle" });
  });
  addRect(s, x + inch(0.3), y + inch(1.8), inch(2.4), inch(0.7), { fill: WHITE, line: INK });
  addText(s, "8", x + inch(0.3), y + inch(1.8), inch(2.4), inch(0.7), { size: 28, bold: true, font: MONO, align: "center", valign: "middle" });
  addArrow(s, x + cw + inch(0.1), y + inch(1.4), inch(8.4), y + inch(1.4), { color: DIM, width: 2 });
  addText(s, "stash", x + cw + inch(0.1), y + inch(0.9), inch(2.0), inch(0.4), { size: 14, italic: true, color: DIM, align: "center" });
  addRect(s, inch(8.4), y + inch(0.8), inch(2.2), inch(1.4), { fill: WHITE, line: INK, lineWidth: 1.5 });
  addText(s, "memory", inch(8.4), y + inch(0.9), inch(2.2), inch(0.4), { size: 14, bold: true, color: DIM, align: "center" });
  addText(s, "8", inch(8.4), y + inch(1.3), inch(2.2), inch(0.8), { size: 44, bold: true, font: MONO, align: "center", valign: "middle" });
  slideCaption(s, "stash an intermediate, recall it later - already half a CPU");
}

// 3
{
  const s = slide();
  slideTitle(s, "What makes a CPU");
  const boxes = [["Program\nmemory", .9, 2], ["Program\ncounter", 3.7, 2], ["Decoder", 6.5, 2], ["Clock", 9.3, 2], ["ALU", 3.7, 4.4], ["RAM", 6.5, 4.4]];
  boxes.forEach(([label, x, y]) => {
    addRect(s, inch(x), inch(y), inch(2.4), inch(1.4), { fill: WHITE, line: INK, lineWidth: 1.5, rounded: true });
    addText(s, label, inch(x), inch(y), inch(2.4), inch(1.4), { size: 22, bold: true, align: "center", valign: "middle" });
  });
  [[3.3, 2.7, 3.7, 2.7, DIM], [6.1, 2.7, 6.5, 2.7, DIM], [7.7, 3.4, 5.5, 4.4, DIM], [6.1, 5.1, 6.5, 5.1, DIM], [9.3, 2.7, 6.1, 2.7, ACCENT]].forEach(([x1, y1, x2, y2, c]) => addArrow(s, inch(x1), inch(y1), inch(x2), inch(y2), { color: c, width: 2 }));
  addRect(s, inch(0.6), inch(6.4), inch(12.1), inch(0.7), { fill: ACCENT, line: null, rounded: true });
  addText(s, "fetch  ->  decode  ->  execute  ->  advance", inch(0.6), inch(6.4), inch(12.1), inch(0.7), { size: 24, bold: true, color: WHITE, align: "center", valign: "middle" });
}

// 4
{
  const s = slide();
  slideTitle(s, "The Von Neumann architecture");
  addRect(s, inch(1.5), inch(2), inch(6.5), inch(3.5), { fill: WHITE, line: INK, lineWidth: 2, rounded: true });
  addText(s, "MEMORY", inch(1.5), inch(2.15), inch(6.5), inch(.4), { size: 14, bold: true, color: DIM, align: "center" });
  addRect(s, inch(1.8), inch(2.8), inch(5.9), inch(1.1), { fill: HIGHLIGHT, line: DIM });
  addText(s, "program", inch(1.8), inch(2.8), inch(5.9), inch(1.1), { size: 28, bold: true, align: "center", valign: "middle" });
  addRect(s, inch(1.8), inch(4.1), inch(5.9), inch(1.1), { fill: LIGHT, line: DIM });
  addText(s, "data", inch(1.8), inch(4.1), inch(5.9), inch(1.1), { size: 28, bold: true, align: "center", valign: "middle" });
  addRect(s, inch(9.5), inch(3.2), inch(2.8), inch(1.4), { fill: ACCENT, line: null, rounded: true });
  addText(s, "CPU", inch(9.5), inch(3.2), inch(2.8), inch(1.4), { size: 36, bold: true, color: WHITE, align: "center", valign: "middle" });
  addArrow(s, inch(7.7), inch(3.35), inch(9.5), inch(3.6), { color: ACCENT, width: 2.5 });
  addText(s, "reads its own instructions", inch(7.8), inch(2.7), inch(2.2), inch(.4), { size: 12, italic: true, color: DIM, align: "center" });
  addArrow(s, inch(7.7), inch(4.65), inch(9.5), inch(4.2), { color: DIM, width: 2 });
  slideCaption(s, "one memory. programs and data both live there.");
}

// 5
{
  const s = slide();
  slideTitle(s, "Today: every layer");
  drawStack(s);
  slideCaption(s, "human-readable code  ->  electrons (well, simulated)");
}

// 6
{
  const s = slide(DARK_BG);
  addText(s, "BY THE END, THIS CPU WILL READ THIS", 0, inch(.6), W, inch(.5), { size: 18, bold: true, color: DIM, align: "center" });
  addText(s, "JCJUM JS DCAFE", 0, inch(2.8), W, inch(2), { size: 120, bold: true, color: HIGHLIGHT, align: "center", font: MONO });
  addRect(s, inch(5.95), inch(5.58), inch(1.0), inch(.62), { fill: ACCENT, line: null, rounded: true });
  addRect(s, inch(6.15), inch(5.18), inch(.6), inch(.55), { fill: TRANSPARENT, line: ACCENT, lineWidth: 8, rounded: true });
}

// 7
{
  const s = slide();
  slideTitle(s, "Meet THMM");
  addRect(s, inch(.8), inch(1.5), inch(5.2), inch(4.4), { fill: WHITE, line: INK, lineWidth: 2, rounded: true });
  addText(s, "THMM", inch(.8), inch(1.65), inch(5.2), inch(.5), { size: 20, bold: true, color: DIM, align: "center" });
  addRect(s, inch(1.3), inch(2.5), inch(2), inch(1), { fill: ACCENT, line: null, rounded: true });
  addText(s, "ACC", inch(1.3), inch(2.5), inch(2), inch(1), { size: 22, bold: true, color: WHITE, align: "center", valign: "middle" });
  addRect(s, inch(3.5), inch(2.5), inch(2), inch(1), { fill: LIGHT, line: INK, rounded: true });
  addText(s, "ALU", inch(3.5), inch(2.5), inch(2), inch(1), { size: 22, bold: true, align: "center", valign: "middle" });
  addRect(s, inch(1.3), inch(4.0), inch(4.2), inch(1.5), { fill: WHITE, line: INK });
  addText(s, "RAM[256]", inch(1.3), inch(4.0), inch(4.2), inch(.4), { size: 14, bold: true, color: DIM, align: "center" });
  for (let c = 0; c < 16; c++) addRect(s, inch(1.4) + c * inch(.255), inch(4.5), inch(.23), inch(.85), { fill: LIGHT, line: DIM });
  addText(s, "9 instructions", inch(7), inch(1.5), inch(5.5), inch(.5), { size: 18, bold: true, color: DIM });
  ["loadm  addr     load mem -> acc", "loadn  imm      load literal -> acc", "store  addr     acc -> mem", "addm   addr     acc += mem", "addn   imm      acc += literal", "subm   addr     acc -= mem", "mulm   addr     acc *= mem", "divm   addr     acc /= mem", "halt            stop"].forEach((line, i) => addText(s, line, inch(7), inch(2.1) + i * inch(.42), inch(5.7), inch(.4), { size: 18, font: MONO }));
  addRect(s, inch(.6), inch(6.4), inch(12.1), inch(.7), { fill: ACCENT, line: null, rounded: true });
  addText(s, "16-bit  *  256 cells  *  9 instructions  *  ~200 lines of Python", inch(.6), inch(6.4), inch(12.1), inch(.7), { size: 22, bold: true, color: WHITE, align: "center", valign: "middle" });
}

// 8
{
  const s = slide();
  slideTitle(s, "The easy case");
  addText(s, "c  =  a + b", 0, inch(1), W, inch(1), { size: 72, bold: true, font: SERIF, align: "center" });
  addArrow(s, W / 2, inch(2.2), W / 2, inch(2.7), { color: DIM, width: 3 });
  addCode(s, "loadm  a\naddm   b\nstore  c", inch(2.5), inch(3), inch(4.5), inch(2.3), { size: 32 });
  addText(s, "accumulator", inch(8), inch(2.7), inch(3.8), inch(.4), { size: 14, bold: true, color: DIM, align: "center" });
  addAccumulatorBox(s, inch(8), inch(3.2), "?", "start");
  addArrow(s, inch(9.3), inch(3.55), inch(9.6), inch(3.55), { color: DIM, width: 2 });
  addAccumulatorBox(s, inch(9.6), inch(3.2), "a", "loadm a");
  addArrow(s, inch(10.9), inch(3.55), inch(11.2), inch(3.55), { color: DIM, width: 2 });
  addAccumulatorBox(s, inch(11.2), inch(3.2), "a+b", "addm b");
  slideCaption(s, "every expression's code leaves its value in the accumulator");
}

// 9
{
  const s = slide();
  slideTitle(s, "The pain");
  addText(s, "(a + b)  x  (c + d)", 0, inch(1), W, inch(1), { size: 64, bold: true, font: SERIF, align: "center" });
  addCode(s, "loadm  a\naddm   b\nstore  t0     <- stash\nloadm  c\naddm   d\nstore  t1     <- stash\nloadm  t0     <- reload\nmulm   t1", inch(2), inch(2.3), inch(5.3), inch(3.8), { size: 22, highlights: [2, 5, 6] });
  addText(s, "memory", inch(8.2), inch(2.1), inch(4), inch(.4), { size: 14, bold: true, color: DIM });
  [["acc", "a+b -> ... -> answer", LIGHT], ["t0", "a + b", HIGHLIGHT], ["t1", "c + d", HIGHLIGHT]].forEach(([lab, val, col], i) => {
    const y = inch(2.5) + i * inch(1);
    addRect(s, inch(8.2), y, inch(1.5), inch(.7), { fill: col, line: INK });
    addText(s, lab, inch(8.2), y, inch(1.5), inch(.7), { size: 20, bold: true, font: MONO, align: "center", valign: "middle" });
    addText(s, val, inch(9.9), y, inch(3), inch(.7), { size: 18, font: MONO, valign: "middle" });
  });
  slideCaption(s, "now imagine 80 of these - by hand - without bugs", { color: ACCENT });
}

// 10
{
  const s = slide();
  slideTitle(s, "A real program");
  addCode(s, "// 3-4-5 right triangle. Expected: hyp_sq = 25.\n\nint a = 4;\nint b = 3;\nint hyp_sq = a * a + b * b;", inch(2.5), inch(2), inch(8.3), inch(3.5), { size: 32 });
  const x = inch(10.5), y = inch(1.4), scale = inch(.5);
  addLine(s, x, y + 3 * scale, x + 4 * scale, y + 3 * scale, { width: 2 });
  addLine(s, x + 4 * scale, y + 3 * scale, x, y, { width: 2 });
  addLine(s, x, y, x, y + 3 * scale, { width: 2 });
  addText(s, "3", x - inch(.3), y + inch(.6), inch(.3), inch(.4), { size: 14, color: DIM });
  addText(s, "4", x + inch(.7), y + inch(1.6), inch(.5), inch(.4), { size: 14, color: DIM });
  addText(s, "?", x + inch(1.2), y + inch(.5), inch(.5), inch(.4), { size: 18, bold: true, color: ACCENT, font: SERIF });
  slideCaption(s, "three lines. compile, run, read RAM[16].");
}

// 11
{
  const s = slide();
  slideTitle(s, "What we got");
  const ox = inch(5.6), oy = inch(4.5), u = inch(.45);
  addLine(s, ox, oy, ox + 4 * u, oy, { width: 3 });
  addLine(s, ox, oy, ox, oy - 3 * u, { width: 3 });
  addLine(s, ox + 4 * u, oy, ox, oy - 3 * u, { color: ACCENT, width: 4 });
  addRect(s, ox, oy, 4 * u, 4 * u, { fill: LIGHT, line: INK });
  addText(s, "16", ox, oy, 4 * u, 4 * u, { size: 44, bold: true, color: DIM, font: SERIF, align: "center", valign: "middle" });
  addRect(s, ox - 3 * u, oy - 3 * u, 3 * u, 3 * u, { fill: LIGHT, line: INK });
  addText(s, "9", ox - 3 * u, oy - 3 * u, 3 * u, 3 * u, { size: 36, bold: true, color: DIM, font: SERIF, align: "center", valign: "middle" });
  addRect(s, inch(8.6), inch(1.6), inch(2.5), inch(2.5), { fill: HIGHLIGHT, line: ACCENT, lineWidth: 3 });
  addText(s, "25", inch(8.6), inch(1.6), inch(2.5), inch(2.5), { size: 84, bold: true, color: ACCENT, font: SERIF, align: "center", valign: "middle" });
  addText(s, "the square on the hypotenuse", inch(8.3), inch(4.2), inch(3.1), inch(.4), { size: 14, italic: true, color: DIM, align: "center" });
  addArrow(s, ox + 4 * u, oy - 1.5 * u, inch(8.6), inch(2.85), { color: ACCENT, width: 2 });
  addRect(s, inch(.8), inch(2), inch(3.2), inch(1.8), { fill: WHITE, line: ACCENT, lineWidth: 3, rounded: true });
  addText(s, "sqrt", inch(.8), inch(2.4), inch(3.2), inch(.7), { size: 44, bold: true, color: DIM, font: MONO, align: "center" });
  addLine(s, inch(1.1), inch(2.3), inch(3.7), inch(3.5), { color: ACCENT, width: 8 });
  addLine(s, inch(3.7), inch(2.3), inch(1.1), inch(3.5), { color: ACCENT, width: 8 });
  addText(s, "not in the instruction set", inch(.8), inch(3.9), inch(3.2), inch(.4), { size: 14, italic: true, color: DIM, align: "center" });
  slideCaption(s, "we can compute the area. the side is not our problem.");
}

// 12
{
  const s = slide();
  slideTitle(s, "Step 1   *   Parse  ->  tree");
  addText(s, "int hyp_sq  =  a * a + b * b ;", 0, inch(1.3), W, inch(.8), { size: 36, bold: true, font: MONO, align: "center" });
  addArrow(s, W / 2, inch(2.3), W / 2, inch(2.8), { color: DIM, width: 3 });
  pythagorasTree(s);
  slideCaption(s, "expressions nest, so they're trees");
}

// 13
{
  const s = slide();
  slideTitle(s, "Haskell  *  the abstract syntax tree");
  addCode(s, "data Expr\n    = Lit   Int\n    | Var   String\n    | BinOp Op Expr Expr\n\ndata Op = Add | Sub | Mul | Div", inch(2.5), inch(2), inch(8.3), inch(3.5), { size: 28, highlights: [3] });
  slideCaption(s, "three lines define the entire expression language");
}

// 14
{
  const s = slide();
  slideTitle(s, "Haskell  *  precedence is data");
  addCode(s, "operatorTable =\n    [ [ binaryL \"*\" Mul, binaryL \"/\" Div ]   <- binds tighter\n    , [ binaryL \"+\" Add, binaryL \"-\" Sub ]   <- binds looser\n    ]", inch(1.5), inch(2.4), inch(10.3), inch(2.6), { size: 24, highlights: [1, 2] });
  slideCaption(s, "row order = precedence. grammar as data, not code.");
}

// 15
{
  const s = slide();
  slideTitle(s, "Codegen  *  easy case");
  const m = treeNode(s, "x", inch(2.8), inch(1.8));
  const a1 = treeNode(s, "a", inch(1.9), inch(3.1), { fill: LIGHT });
  const a2 = treeNode(s, "a", inch(3.7), inch(3.1), { fill: LIGHT });
  treeEdge(s, m, a1); treeEdge(s, m, a2);
  addArrow(s, inch(4.5), inch(2.6), inch(5.4), inch(2.6), { color: DIM, width: 3 });
  addCode(s, "loadm  a\nmulm   a", inch(5.6), inch(2), inch(3.3), inch(1.5), { size: 32 });
  addText(s, "accumulator", inch(9.5), inch(1.6), inch(3.3), inch(.4), { size: 14, bold: true, color: DIM });
  addAccumulatorBox(s, inch(9.5), inch(2), "?", "start");
  addAccumulatorBox(s, inch(9.5), inch(3.2), "a", "loadm a");
  addAccumulatorBox(s, inch(9.5), inch(4.4), "a^2", "mulm a");
  slideCaption(s, "leaves emit one instruction. the contract: value lives in the accumulator.");
}

// 16
{
  const s = slide();
  slideTitle(s, "Codegen  *  the temp dance");
  pythagorasTree(s, inch(3), inch(1.3), inch(1.4));
  addCode(s, "loadm  a\nmulm   a\nstore  t0     <- stash a^2\nloadm  b\nmulm   b\nstore  t1     <- stash b^2\nloadm  t0     <- reload\naddm   t1\nstore  hyp_sq", inch(6), inch(1.6), inch(4.5), inch(4.6), { size: 20, highlights: [2, 5, 6] });
  [["acc", ACCENT, WHITE, 2], ["t0", HIGHLIGHT, INK, 3], ["t1", HIGHLIGHT, INK, 4]].forEach(([label, fill, color, row]) => {
    addRect(s, inch(11), inch(row), inch(1.5), inch(.7), { fill, line: fill === ACCENT ? null : INK, rounded: true });
    addText(s, label, inch(11), inch(row), inch(1.5), inch(.7), { size: 18, bold: true, color, font: MONO, align: "center", valign: "middle" });
  });
  slideCaption(s, "stash the left, compute the right, recombine");
}

// 17
{
  const s = slide();
  slideTitle(s, "Haskell  *  the codegen function");
  addCode(s, "genExpr _    (Lit n)        = ...   -- emit loadn\ngenExpr vars (Var x)        = ...   -- emit loadm\ngenExpr vars (BinOp op l r) = ...   -- recurse: l, then r, combine", inch(.6), inch(2.6), inch(12.1), inch(2.4), { size: 22 });
  slideCaption(s, "pattern-matches on tree shape. leaves emit; branches recurse.");
}

// 18
{
  const s = slide();
  slideTitle(s, "Step 3   *   Link   *   names -> addresses");
  addText(s, "before", inch(1), inch(1.4), inch(4), inch(.4), { size: 16, bold: true, color: DIM });
  addCode(s, "loadm  a\nmulm   a\nstore  t0\nloadm  b\nmulm   b\nstore  t1\nloadm  t0\naddm   t1\nstore  hyp_sq\nhalt", inch(1), inch(1.8), inch(4), inch(4.4), { size: 18 });
  addArrow(s, inch(5.4), inch(4), inch(6), inch(4), { color: ACCENT, width: 3 });
  addText(s, "after", inch(6.2), inch(1.4), inch(4), inch(.4), { size: 16, bold: true, color: DIM });
  addCode(s, " 4: loadm  14\n 5: mulm   14\n 6: store  17\n 7: loadm  15\n 8: mulm   15\n 9: store  18\n10: loadm  17\n11: addm   18\n12: store  16\n13: halt", inch(6.2), inch(1.8), inch(4), inch(4.4), { size: 18 });
  addText(s, "address table", inch(10.5), inch(1.4), inch(2.5), inch(.4), { size: 14, bold: true, color: DIM });
  addRect(s, inch(10.5), inch(1.8), inch(2.5), inch(2.2), { fill: LIGHT, line: DIM });
  [["a", "14"], ["b", "15"], ["hyp_sq", "16"], ["t0", "17"], ["t1", "18"]].forEach(([name, addr], i) => {
    const y = inch(1.9) + i * inch(.4);
    addText(s, name, inch(10.7), y, inch(1.2), inch(.4), { size: 18, font: MONO });
    addText(s, "->", inch(11.8), y, inch(.4), inch(.4), { size: 18, color: DIM, font: MONO });
    addText(s, addr, inch(12.1), y, inch(.7), inch(.4), { size: 18, bold: true, color: ACCENT, font: MONO });
  });
}

// 19
{
  const s = slide();
  slideTitle(s, "Same program. four ways.");
  addText(s, "source  (.thcc)", inch(.6), inch(1.15), inch(6.1), inch(.3), { size: 12, bold: true, color: DIM });
  addCode(s, "int a = 4;\nint b = 3;\nint hyp_sq = a * a + b * b;", inch(.6), inch(1.45), inch(6.1), inch(2.35), { size: 18 });
  addText(s, "AST", inch(6.6), inch(1.15), inch(6.1), inch(.3), { size: 12, bold: true, color: DIM });
  pythagorasTree(s, inch(9.6), inch(1.55), inch(1.2));
  addText(s, "assembly  (.asm)", inch(.6), inch(4.15), inch(6.1), inch(.3), { size: 12, bold: true, color: DIM });
  addCode(s, " 0: loadn  4\n 1: store  14\n 2: loadn  3\n 3: store  15\n 4: loadm  14\n 5: mulm   14\n 6: store  17\n 7: loadm  15\n 8: mulm   15\n 9: store  18\n10: loadm  17\n11: addm   18\n12: store  16\n13: halt", inch(.6), inch(4.45), inch(6.1), inch(2.35), { size: 13 });
  addText(s, "machine code  (.hex / .bits)", inch(6.6), inch(4.15), inch(6.1), inch(.3), { size: 12, bold: true, color: DIM });
  addCode(s, "0x3004    0011 0000 0000 0100\n0x400E    0100 0000 0000 1110\n0x3003    0011 0000 0000 0011\n0x400F    0100 0000 0000 1111\n0x200E    0010 0000 0000 1110\n0xB00E    1011 0000 0000 1110\n0x4011    0100 0000 0001 0001\n0x200F    0010 0000 0000 1111\n0xB00F    1011 0000 0000 1111\n0x4012    0100 0000 0001 0010\n0x2011    0010 0000 0001 0001\n0x7012    0111 0000 0001 0010\n0x4010    0100 0000 0001 0000\n0x1000    0001 0000 0000 0000", inch(6.6), inch(4.45), inch(6.1), inch(2.35), { size: 11 });
}

// 20
{
  const s = slide();
  slideTitle(s, "Caesar Cipher");
  [["Used in Roman military dispatches.", "~50 BC"], ["Each letter shifted by a fixed key.", "shift 3: A -> D, B -> E, C -> F"], ["Trivially broken by frequency analysis.", "but it's the ancestor of every cipher since"], ["ROT13 (shift 13) is still used today.", "spoiler tags on the internet"]].forEach(([head, sub], i) => {
    const y = inch(2) + i * inch(1);
    addRect(s, inch(.8), y + inch(.18), inch(.18), inch(.18), { fill: ACCENT, line: null, rounded: true });
    addText(s, head, inch(1.2), y, inch(7), inch(.5), { size: 24, bold: true });
    addText(s, sub, inch(1.2), y + inch(.45), inch(7), inch(.4), { size: 16, italic: true, color: DIM });
  });
  const cx = inch(10.5), cy = inch(4.2), outer = inch(1.6), inner = inch(1);
  addRect(s, cx - outer, cy - outer, outer * 2, outer * 2, { fill: LIGHT, line: INK, lineWidth: 2, rounded: true });
  ["A", "N", "G", "T"].forEach((letter, i) => {
    const pos = [[0, -1.25], [0, 1.05], [-1.25, -0.2], [1.05, -0.2]][i];
    addText(s, letter, cx + inch(pos[0]) - inch(.2), cy + inch(pos[1]), inch(.4), inch(.4), { size: 18, bold: true, font: SERIF, align: "center" });
  });
  addRect(s, cx - inner, cy - inner, inner * 2, inner * 2, { fill: ACCENT, line: null, rounded: true });
  addText(s, "shift", cx - inner, cy - inch(.4), inner * 2, inch(.4), { size: 14, bold: true, color: WHITE, align: "center" });
  addText(s, "3", cx - inner, cy, inner * 2, inch(.7), { size: 44, bold: true, color: WHITE, font: SERIF, align: "center" });
}

// 21
{
  const s = slide();
  slideTitle(s, "Every time you press Run");
  drawStack(s, new Set([0, 1, 2, 3, 4]));
  slideCaption(s, "parse  *  generate  *  link  *  execute");
}

const out = "THCC_presentation.pptx";
const pptx = await PresentationFile.exportPptx(ppt);
await pptx.save(out);
console.log(`wrote ${out}: ${ppt.slides.count} slides`);
