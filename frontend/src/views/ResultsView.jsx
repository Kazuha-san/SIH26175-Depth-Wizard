/**
 * View 3 -- Results. The main workspace.
 * Layout: TerrainCanvas (3D viewport, dominant) + side panel
 * (DSM stats, calibration detail, accuracy, height profile, point inspector).
 */
import TerrainCanvas from '../components/viewport/TerrainCanvas.jsx'
import DSMStatsCard from '../components/panel/DSMStatsCard.jsx'
import CalibrationDetailCard from '../components/panel/CalibrationDetailCard.jsx'
import AccuracyPanel from '../components/panel/AccuracyPanel.jsx'
import HeightProfileTool from '../components/panel/HeightProfileTool.jsx'
import PointInspector from '../components/panel/PointInspector.jsx'

export default function ResultsView({ onReset }) {
  return (
    <div className="results-view">
      <TerrainCanvas />
      <div className="side-panel">
        <DSMStatsCard />
        <CalibrationDetailCard />
        <AccuracyPanel />
        <HeightProfileTool />
        <PointInspector />
      </div>
    </div>
  )
}
