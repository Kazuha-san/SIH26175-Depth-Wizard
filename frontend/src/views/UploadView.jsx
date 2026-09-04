/**
 * View 1 -- Upload & Setup.
 * Contains: FileDropZone, InputTypeBadge, image preview, MetadataPanel,
 * terrain type selector, "Run Pipeline" button.
 * On submit -> POST /upload, then calls onStart() to move to Processing view.
 */
import FileDropZone from '../components/upload/FileDropZone.jsx'
import InputTypeBadge from '../components/upload/InputTypeBadge.jsx'
import MetadataPanel from '../components/upload/MetadataPanel.jsx'

export default function UploadView({ onStart }) {
  // TODO: hold selected file + detected input type in local state
  return (
    <div className="upload-view">
      <FileDropZone />
      <InputTypeBadge />
      <MetadataPanel />
      {/* TODO: "Run Pipeline" button -> onStart() */}
    </div>
  )
}
