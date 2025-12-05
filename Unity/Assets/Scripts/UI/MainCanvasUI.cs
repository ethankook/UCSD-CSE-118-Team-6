using System;
using System.Linq;
using Oculus.Interaction.Samples;
using TMPro;
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
    [SerializeField] private TextMeshProUGUI statusText;
    [SerializeField] private VRDropDownUI preferredLanguageDropdown;

    void Start()
    {
        if (toggleFollowButton != null)
        {
            toggleFollowButton.onClick.AddListener(ToggleFollowCamera);
        }
        if (preferredLanguageDropdown != null)
        {
            preferredLanguageDropdown.OnSelectionChanged += OnPreferredLanguageChanged;
            preferredLanguageDropdown.Populate(Enum.GetNames(typeof(LanguageCode)).ToList());
        }
    }
    [ContextMenu("Toggle Follow Camera")]
    private void ToggleFollowCamera()
    {
        FollowCamera = !FollowCamera;
    }
    [ContextMenu("Update Preferred Language")]
    private void OnPreferredLanguageChanged(string selectedText)
    {
        if (Enum.TryParse<LanguageCode>(selectedText, out var languageCode))
        {
            ConfigService.SetPreferredLanguage(languageCode);
        }
        else
        {
            LogService.LogError($"Invalid language selection: {selectedText}");
        }
    }
}
