/**
 * View 2 -- Processing.
 * Polls/awaits the backend's /process/{image_id} call, shows the
 * StageStepper + live log + intermediate preview thumbnails.
 * Calls onDone() once the backend returns final results.
 */
import StageStepper from '../components/processing/StageStepper.jsx'
import LogPanel from '../components/processing/LogPanel.jsx'

export default function ProcessingView({ onDone }) {
  // TODO: kick off /process/{image_id} on mount, track stage progress
  return (
    <div className="processing-view">
      <StageStepper />
      <LogPanel />
    </div>
  )
}
