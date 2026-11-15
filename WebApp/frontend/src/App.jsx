import { BrowserRouter, HashRouter, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout.jsx'
import AISystems from './pages/AISystems.jsx'
import MarsExplorer from './pages/MarsExplorer.jsx'
import MissionOverview from './pages/MissionOverview.jsx'
import NotFound from './pages/NotFound.jsx'
import RoutePlanner from './pages/RoutePlanner.jsx'
import ScientificTargets from './pages/ScientificTargets.jsx'
import TerrainAnalysis from './pages/TerrainAnalysis.jsx'
import AeolianIntelligence from './components/aeolian/AeolianIntelligence.jsx'
import KanbanBoard from './components/kanban/KanbanBoard.jsx'

export default function App() {
  const Router = import.meta.env.VITE_ROUTER_MODE === "hash" ? HashRouter : BrowserRouter
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<MissionOverview />} />
          <Route path="explorer" element={<MarsExplorer />} />
          <Route path="terrain" element={<TerrainAnalysis />} />
          <Route path="routes" element={<RoutePlanner />} />
          <Route path="targets" element={<ScientificTargets />} />
          <Route path="ai" element={<AISystems />} />
          <Route path="aeolian" element={<AeolianIntelligence />} />
          <Route path="kanban" element={<KanbanBoard />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  )
}