using UnityEngine;
using UnityEngine.UI;

public class MainCanvasUI : MonoBehaviour
{
    private bool _followCamera = true;
    public bool FollowCamera 
    { 
        get => _followCamera; 
        set 
        {
            if (_followCamera != value)
            {
                _followCamera = value;
                if (_followCamera)
                {
                    transform.SetParent(cameraTransform);
                }
                else
                {
                    transform.SetParent(null);
                }
            }
        } 
    }

    [SerializeField] private Transform cameraTransform;
    [SerializeField] private Vector3 offsetFromCamera = new Vector3(0, 0.7f, 0.2f);
    [SerializeField] private Button toggleFollowButton;

    void Start()
    {
        if (toggleFollowButton != null)
        {
            toggleFollowButton.onClick.AddListener(ToggleFollowCamera);
        }
    }

    private void ToggleFollowCamera()
    {
        FollowCamera = !FollowCamera;
    }
}
