/**
 * Thin wrapper around fetch() calls to the local FastAPI backend
 * (localhost:8000). Every network call in the app should go through
 * here -- no raw fetch() calls scattered in components.
 */
const BASE_URL = 'http://localhost:8000'

export async function uploadImage(file) {
  // TODO: POST /upload with FormData, return {image_id, input_type, metadata}
  throw new Error('not implemented')
}

export async function runPipeline(imageId) {
  // TODO: POST /process/{image_id}, return final pipeline result
  throw new Error('not implemented')
}

export async function getResult(imageId) {
  // TODO: GET /result/{image_id}
  throw new Error('not implemented')
}
