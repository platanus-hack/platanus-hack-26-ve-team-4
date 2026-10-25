import { describe, expect, it } from "vitest";
import {
  addToBatch,
  BATCH_IDLE_MS,
  BATCH_MAX_MESSAGES,
  BATCH_MAX_WAIT_MS,
  dueAt,
  isBatch,
  isDue,
  packBatch,
} from "./batch";

describe("lote de mensajes", () => {
  it("fija las constantes acordadas: 10 s, 20 s y 4 mensajes", () => {
    expect([BATCH_IDLE_MS, BATCH_MAX_WAIT_MS, BATCH_MAX_MESSAGES]).toEqual([10_000, 20_000, 4]);
  });

  it("cada mensaje reinicia la espera sin pasar del tope desde el primero", () => {
    const one = addToBatch(null, "uno", 0);
    expect(dueAt(one)).toBe(10_000);
    const two = addToBatch(one, "dos", 6_000);
    expect(two).toEqual({ texts: ["uno", "dos"], first: 0, last: 6_000 });
    expect(dueAt(two)).toBe(16_000);
    expect(dueAt(addToBatch(two, "tres", 15_000))).toBe(20_000);
  });

  it("vence por tiempo, al llegar al máximo de mensajes o con «Enviar ahora»", () => {
    const batch = addToBatch(null, "uno", 0);
    expect(isDue(batch, 9_999)).toBe(false);
    expect(isDue(batch, 10_000)).toBe(true);
    expect(isDue({ ...batch, now: true }, 0)).toBe(true);
    const full = ["dos", "tres", "cuatro"].reduce((acc, text) => addToBatch(acc, text, 1), batch);
    expect(isDue(full, 1)).toBe(true);
    expect(isDue(addToBatch(batch, "dos", 1), 1, 2)).toBe(true);
  });

  it("une con saltos de línea y divide en mensajes si no cabe en el largo máximo", () => {
    expect(packBatch(["uno", "dos"], 4000)).toEqual(["uno\ndos"]);
    expect(packBatch(["12345", "6789"], 10)).toEqual(["12345\n6789"]);
    expect(packBatch(["123456", "abcdef"], 10)).toEqual(["123456", "abcdef"]);
  });

  it("valida el lote leído del navegador", () => {
    expect(isBatch({ texts: ["Hola"], first: 1, last: 2 })).toBe(true);
    expect(isBatch({ texts: ["Hola"], first: 1, last: 2, now: true })).toBe(true);
    expect(isBatch(null)).toBe(false);
    expect(isBatch({ texts: [], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["  "], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["a", "b", "c", "d", "e"], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["Hola"], first: "1", last: 2 })).toBe(false);
  });
});
