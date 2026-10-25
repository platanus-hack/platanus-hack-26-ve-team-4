import { useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router";
import { BoardPage } from "../features/board/BoardPage";
import { MonitorPage } from "../features/monitor/MonitorPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

function Navigation({ hidden }: { hidden: boolean }) {
  // La Arena en vivo se proyecta a pantalla completa: sin barra mientras está abierta con el secreto. En el acceso y tras «Salir» la barra vuelve.
  if (hidden) return null;
  return (
    <nav className="page controls" aria-label="Principal">
      <Link to="/">Participar</Link>
      <Link to="/arena">Arena en vivo</Link>
      <Link to="/monitor">Monitor</Link>
      <Link to="/operator">Operación</Link>
    </nav>
  );
}

export function App() {
  const [projecting, setProjecting] = useState(false);
  return (
    <BrowserRouter>
      <Navigation hidden={projecting} />
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<BoardPage onProjectingChange={setProjecting} />} />
        <Route path="/monitor" element={<MonitorPage />} />
        <Route path="/operator" element={<OperatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}
