import { BrowserRouter, Link, Route, Routes } from "react-router";
import { ArenaPage } from "../features/arena/ArenaPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

export function App() {
  return (
    <BrowserRouter>
      <nav className="page controls" aria-label="Principal">
        <Link to="/">Participar</Link>
        <Link to="/arena">Arena en vivo</Link>
        <Link to="/operator">Operación</Link>
      </nav>
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<ArenaPage />} />
        <Route path="/operator" element={<OperatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}
