import * as THREE from "three";

export const loadTextureFromBase64 = (base64) => {
  if (!base64) {
    return Promise.reject(new Error("Terrain texture is missing."));
  }

  const source = base64.includes(",") ? base64 : `data:image/png;base64,${base64}`;

  return new Promise((resolve, reject) => {
    const loader = new THREE.TextureLoader();

    loader.load(
      source,
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.needsUpdate = true;
        resolve(texture);
      },
      undefined,
      reject,
    );
  });
};

export default loadTextureFromBase64;
