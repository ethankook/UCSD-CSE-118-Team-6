using System;
using System.Collections.Generic;
using Oculus.Interaction.Samples;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class VRDropDownUI : MonoBehaviour
{
    [Header("Meta Integration")]
    
    // Drag the main label (The one always visible)
    [SerializeField] private TextMeshProUGUI mainLabel;
    [SerializeField] private Toggle dropdownListButtonToggle;

    [Header("Configuration")]
    [SerializeField] private GameObject itemPrefab; // Your button prefab
    [SerializeField] private RectTransform contentParent; // The parent for the list items, it should contain a group alpha toggle to fade in/out

    [SerializeField] private ToggleGroup toggleGroup; // The ToggleGroup for the items
    // Event for your other scripts to listen to
    public event Action<string> OnSelectionChanged;

    public void Populate(List<string> options)
    {
        if (!toggleGroup)
        {
            toggleGroup = gameObject.AddComponent<ToggleGroup>();
        }
        // 1. Clear old items, skip the first one (gradient background)
        for(int i = contentParent.childCount - 1; i >= 1; i--)
        {
            Destroy(contentParent.GetChild(i).gameObject);
        }


        // 2. Create new items
        foreach (string optionText in options)
        {
            CreateItem(optionText);
        }
    }

    private void CreateItem(string text)
    {
        GameObject newItem = Instantiate(itemPrefab, contentParent);

        // Setup Text
        var tmp = newItem.GetComponentInChildren<TextMeshProUGUI>();
        if (tmp) tmp.text = text;

        // Setup Interaction
        // We use the standard Button component which works with Meta's PointableCanvas
        Toggle btn = newItem.GetComponent<Toggle>();
        if (btn)
        {
            btn.onValueChanged.AddListener((isOn) => { if (isOn) OnItemClicked(text); });
            btn.group = toggleGroup;
        }
    }

    private void OnItemClicked(string selectedText)
    {
        // 1. Update the header
        if (mainLabel) mainLabel.text = selectedText;

        // 2. Notify other scripts
        OnSelectionChanged?.Invoke(selectedText);

        // 3. Close the dropdown
        // Since we have the reference to the list object, we can just close it directly.
        // This works regardless of what the "DropDownGroup" script thinks.
        if (contentParent)
        {
            dropdownListButtonToggle.isOn = false; // click the toggle group to close it
        }
    }
}
