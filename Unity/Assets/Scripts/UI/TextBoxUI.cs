using System;
using System.Collections;
using Meta.XR.ImmersiveDebugger.UserInterface.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class TextBoxUI : MonoBehaviour
{
    [SerializeField] GameObject textEntryPrefab;
    [SerializeField] RectTransform contentArea;
    [SerializeField] ScrollRect scrollRect;

    /// <summary>
    /// this is used so that if the new text entry starts with all text in the previous text entry, we update the previous text entry instead of creating a new one
    /// </summary>
    TextEntryUI previousEntry;

    void Start()
    {
        if (!scrollRect)
        {
            scrollRect = GetComponent<ScrollRect>();
        }
    }

    public void AddTextEntry(string text, Sprite icon = null, Color color = default)
    {
        if (text == null || text == "" || string.IsNullOrEmpty(text)) return;
        Debug.Log(text);
        if (previousEntry && text.StartsWith(previousEntry.Text))
        {
            previousEntry.Text = text;
            return;
        }
        TextEntryUI entry = Instantiate(textEntryPrefab, contentArea).GetComponent<TextEntryUI>();
        entry.init(text, icon, color);
        Canvas.ForceUpdateCanvases();
        scrollRect.verticalNormalizedPosition = 0f;
        previousEntry = entry;
    }
    public void ClearText()
    {
        foreach (Transform child in contentArea)
        {
            Destroy(child.gameObject);
        }
    }
}

