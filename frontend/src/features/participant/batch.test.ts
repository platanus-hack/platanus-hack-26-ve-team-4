import { describe, expect, it } from "vitest";
import {
  addToBatch,
  BATCH_IDLE_MS,
  isBatch,
  isDue,
  packBatch,
  QUEUE_MAX,
  TYPING_DELAY_MS,
} from "./batch";

describe("lote de mensajes", () => {
  it("fija las constantes acordadas: 10 s de silencio, 4 s para escribir y 10 mensajes", () => {
    expect([BATCH_IDLE_MS, TYPING_DELAY_MS, QUEUE_MAX]).toEqual([10_000, 4_000, 10]);
  });

  it("agrega al final y conserva el primer instante", () => {
    const one = addToBatch(null, "uno", 0);
    expect(addToBatch(one, "dos", 6_000)).toEqual({ texts: ["uno", "dos"], first: 0, last: 6_000 });
  });

  it("vence a los 10 s del último mensaje o al llegar al máximo", () => {
    const two = addToBatch(addToBatch(null, "uno", 0), "dos", 6_000);
    expect(isDue(two, 15_999, QUEUE_MAX, BATCH_IDLE_MS)).toBe(false);
    expect(isDue(two, 16_000, QUEUE_MAX, BATCH_IDLE_MS)).toBe(true);
    expect(isDue(two, 6_000, 2, BATCH_IDLE_MS)).toBe(true);
  });

  it("une con saltos de línea y agrupa sin pasar el largo máximo", () => {
    expect(packBatch(["uno", "dos"], 4000)).toEqual(["uno\ndos"]);
    expect(packBatch(["12345", "6789"], 10)).toEqual(["12345\n6789"]);
    expect(packBatch(["123456", "abcdef"], 10)).toEqual(["123456", "abcdef"]);
    expect(packBatch(["abc", "def", "ghijklmn"], 8)).toEqual(["abc\ndef", "ghijklmn"]);
  });

  it("valida el lote leído del navegador", () => {
    expect(isBatch({ texts: ["Hola"], first: 1, last: 2 })).toBe(true);
    expect(isBatch(null)).toBe(false);
    expect(isBatch({ texts: [], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["  "], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: Array(11).fill("a"), first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["Hola"], first: "1", last: 2 })).toBe(false);
  });
});
