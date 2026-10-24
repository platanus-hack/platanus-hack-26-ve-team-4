import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router";
import { ArenaPage } from "../features/arena/ArenaPage";
import { BoardPage } from "../features/board/BoardPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

function Navigation() {
  // El tablero se proyecta a pantalla completa: sin barra de navegación.
  if (useLocation().pathname === "/tablero") return null;
  return (
    <nav className="page controls" aria-label="Principal">
      <Link to="/">Participar</Link>
      <Link to="/arena">Arena en vivo</Link>
      <Link to="/operator">Operación</Link>
      <Link to="/tablero">Tablero de ataque</Link>
    </nav>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<ArenaPage />} />
        <Route path="/operator" element={<OperatorPage />} />
        <Route path="/tablero" element={<BoardPage />} />
      </Routes>
    </BrowserRouter>
  );
}
