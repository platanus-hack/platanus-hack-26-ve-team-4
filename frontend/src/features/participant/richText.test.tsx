import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { richText } from "./richText";

const html = (text: string) => render(<p>{richText(text)}</p>).container.innerHTML;

describe("richText", () => {
  it("pone en negrita lo que va entre dobles asteriscos", () => {
    expect(html("2. **Políticas**: envíos")).toBe("<p>2. <strong>Políticas</strong>: envíos</p>");
  });

  it("cambia las viñetas de guion o asterisco por un punto", () => {
    expect(html("Opciones:\n- uno\n* dos")).toBe("<p>Opciones:\n• uno\n• dos</p>");
  });

  it("no interpreta HTML del modelo", () => {
    expect(html("<b>hola</b> **ok**")).toBe("<p>&lt;b&gt;hola&lt;/b&gt; <strong>ok</strong></p>");
  });

  it("deja igual un texto sin marcas y un asterisco suelto", () => {
    expect(html("Total 3 * 2 y **sin cerrar")).toBe("<p>Total 3 * 2 y **sin cerrar</p>");
  });
});
