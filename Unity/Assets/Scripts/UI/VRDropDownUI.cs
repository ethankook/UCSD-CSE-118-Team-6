using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class VRDropDownUI : MonoBehaviour
{
[Header("Meta Integration")]
    // Drag the object containing the List items here (The one that toggles on/off)
    [SerializeField] private GameObject listContainerObject; 
    
    // Drag the main label (The one always visible)
    [SerializeField] private TextMeshProUGUI mainLabel;

    [Header("Configuration")]
    [SerializeField] private GameObject itemPrefab; // Your button prefab
    [SerializeField] private Transform contentParent; // The parent for the list items

    // Event for your other scripts to listen to
    public event Action<string> OnSelectionChanged;

    private void Start()
    {
        // Example usage: Initialize with some default data
        // Populate(new List<string> { "Option A", "Option B", "Option C" });
    }

    public void Populate(List<string> options)
    {
        // 1. Clear old items
        foreach (Transform child in contentParent)
            Destroy(child.gameObject);

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
        if (listContainerObject)
        {
            listContainerObject.SetActive(false);
        }
    }
}
