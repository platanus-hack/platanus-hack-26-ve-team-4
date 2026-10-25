import { describe, expect, it } from "vitest";
import { addToBatch, isBatch, packBatch, QUEUE_MAX } from "./batch";

describe("cola de mensajes", () => {
  it("admite hasta 10 mensajes sin respuesta", () => {
    expect(QUEUE_MAX).toBe(10);
  });

  it("agrega al final y conserva el primer instante", () => {
    const one = addToBatch(null, "uno", 0);
    expect(addToBatch(one, "dos", 6_000)).toEqual({ texts: ["uno", "dos"], first: 0, last: 6_000 });
  });

  it("une con saltos de línea y agrupa sin pasar el largo máximo", () => {
    expect(packBatch(["uno", "dos"], 4000)).toEqual(["uno\ndos"]);
    expect(packBatch(["12345", "6789"], 10)).toEqual(["12345\n6789"]);
    expect(packBatch(["123456", "abcdef"], 10)).toEqual(["123456", "abcdef"]);
    expect(packBatch(["abc", "def", "ghijklmn"], 8)).toEqual(["abc\ndef", "ghijklmn"]);
  });

  it("valida la cola leída del navegador", () => {
    expect(isBatch({ texts: ["Hola"], first: 1, last: 2 })).toBe(true);
    expect(isBatch(null)).toBe(false);
    expect(isBatch({ texts: [], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["  "], first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: Array(11).fill("a"), first: 1, last: 2 })).toBe(false);
    expect(isBatch({ texts: ["Hola"], first: "1", last: 2 })).toBe(false);
  });
});
