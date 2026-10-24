import { BrowserRouter, Route, Routes } from "react-router";
import { ArenaPage } from "../features/arena/ArenaPage";
import { OperatorPage } from "../features/operator/OperatorPage";
import { ParticipantPage } from "../features/participant/ParticipantPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ParticipantPage />} />
        <Route path="/arena" element={<ArenaPage />} />
        <Route path="/operator" element={<OperatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}
