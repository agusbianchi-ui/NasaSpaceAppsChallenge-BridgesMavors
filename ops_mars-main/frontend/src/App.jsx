import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout.jsx'
import AISystems from './pages/AISystems.jsx'
import MarsExplorer from './pages/MarsExplorer.jsx'
import MissionOverview from './pages/MissionOverview.jsx'
import NotFound from './pages/NotFound.jsx'
import RoutePlanner from './pages/RoutePlanner.jsx'
import ScientificTargets from './pages/ScientificTargets.jsx'
import TerrainAnalysis from './pages/TerrainAnalysis.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<MissionOverview />} />
          <Route path="explorer" element={<MarsExplorer />} />
          <Route path="terrain" element={<TerrainAnalysis />} />
          <Route path="routes" element={<RoutePlanner />} />
          <Route path="targets" element={<ScientificTargets />} />
          <Route path="ai" element={<AISystems />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
