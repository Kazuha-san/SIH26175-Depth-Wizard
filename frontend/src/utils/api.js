const API_BASE = "http://localhost:8000";

const parseErrorDetail = async (response) => {
  try {
    const body = await response.json();
    return body?.detail || response.statusText;
  } catch {
    return response.statusText;
  }
};

/**
 * Uploads a file and returns { image_id, input_type, metadata }.
 * Does NOT run the pipeline yet -- see processImage.
 */
export const uploadImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${await parseErrorDetail(response)}`);
  }

  return response.json();
};

/**
 * Runs the full Stage1->2->3 pipeline on a previously uploaded image.
 * This is the slow call (depth inference + calibration + mesh export) --
 * callers should show a processing/loading state while it's in flight.
 */
export const processImage = async (imageId) => {
  const response = await fetch(`${API_BASE}/process/${imageId}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Processing failed: ${await parseErrorDetail(response)}`);
  }

  return response.json();
};

/**
 * Fetches the cached result for an already-processed image.
 * Not used in the main upload->process flow (processImage's response IS
 * the result), but useful for re-fetching after a page refresh.
 */
export const getResult = async (imageId) => {
  const response = await fetch(`${API_BASE}/result/${imageId}`);

  if (!response.ok) {
    throw new Error(`Fetching result failed: ${await parseErrorDetail(response)}`);
  }

  return response.json();
};
