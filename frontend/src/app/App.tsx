import { BrowserRouter, Link, Route, Routes } from "react-router";
import { ArenaPage } from "../features/arena/ArenaPage";
import { MonitorPage } from "../features/monitor/MonitorPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

export function App() {
  return (
    <BrowserRouter>
      <nav className="page controls" aria-label="Principal">
        <Link to="/">Participar</Link>
        <Link to="/arena">Arena en vivo</Link>
        <Link to="/monitor">Monitor</Link>
        <Link to="/operator">Operación</Link>
      </nav>
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<ArenaPage />} />
        <Route path="/monitor" element={<MonitorPage />} />
        <Route path="/operator" element={<OperatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}
