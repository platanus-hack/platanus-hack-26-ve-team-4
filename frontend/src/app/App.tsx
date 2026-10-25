import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router";
import { BoardPage } from "../features/board/BoardPage";
import { MonitorPage } from "../features/monitor/MonitorPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

function Navigation() {
  // La Arena en vivo se proyecta a pantalla completa: sin barra de navegación.
  if (useLocation().pathname === "/arena") return null;
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
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<BoardPage />} />
        <Route path="/monitor" element={<MonitorPage />} />
        <Route path="/operator" element={<OperatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}
