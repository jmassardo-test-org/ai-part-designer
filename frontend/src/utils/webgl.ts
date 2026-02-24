/**
 * WebGL support detection utility.
 *
 * Provides a simple check for whether the current browser supports
 * WebGL rendering contexts, used to gate 3D viewer components.
 */

/**
 * Detect whether the current browser supports WebGL.
 *
 * @returns `true` when a WebGL rendering context can be created.
 */
export function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}
