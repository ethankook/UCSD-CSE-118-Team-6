using UnityEngine;
using UnityEngine.EventSystems;

public class CameraAlwaysShowRay : MonoBehaviour
{
    public OVRInputModule inputModule; // Drag OVRInputModule here
    private LineRenderer lineRenderer;

    void Start()
    {
        lineRenderer = GetComponent<LineRenderer>();
        lineRenderer.useWorldSpace = true;
    }

    void Update()
    {
        // 1. Get the ray from the OVR Input Module (The "Brain")
        if (inputModule != null && inputModule.rayTransform != null)
        {
            Transform rayOrigin = inputModule.rayTransform;
            
            // 2. Set Start Point (Controller)
            lineRenderer.SetPosition(0, rayOrigin.position);

            // 3. Set End Point
            // The Input Module knows where the cursor is. 
            // If it's hitting something, it gives us the distance or hit point.
            // But for simplicity, we often just raycast ourselves or use a fixed length:
            Vector3 endPos = rayOrigin.position + (rayOrigin.forward * 2.0f);
            
            // Check if OVRInputModule has a "RaycastResult" (requires digging into module)
            // Easier approach: Raycast against UI layer manually to match visual
            RaycastHit hit;
            if (Physics.Raycast(rayOrigin.position, rayOrigin.forward, out hit, 5.0f))
            {
                // Only shorten line if we hit UI
                 if (hit.collider.gameObject.GetComponent<UnityEngine.UI.Graphic>() != null || 
                     hit.collider.gameObject.GetComponent<Collider>() != null) 
                 {
                    endPos = hit.point;
                 }
            }
            
            lineRenderer.SetPosition(1, endPos);
        }
    }
}
