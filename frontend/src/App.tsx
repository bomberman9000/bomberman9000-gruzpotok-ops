import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Analytics } from "./pages/Analytics";
import { CallByRequest, CallDetail } from "./pages/CallDetail";
import { CaseEntry } from "./pages/CaseEntry";
import { CasePanelPage } from "./pages/CasePanelPage";
import { Dashboard } from "./pages/Dashboard";
import { History } from "./pages/History";
import { ReviewQueue } from "./pages/ReviewQueue";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="queue" element={<ReviewQueue />} />
        <Route path="history" element={<History />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="case" element={<CaseEntry />} />
        <Route path="panels/:kind/:entityId" element={<CasePanelPage />} />
        <Route path="calls/by-request/:requestId" element={<CallByRequest />} />
        <Route path="calls/:callId" element={<CallDetail />} />
      </Route>
    </Routes>
  );
}
