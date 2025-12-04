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

    void Start()
    {
        if (!scrollRect)
        {
            scrollRect = GetComponent<ScrollRect>();
        }
    }

    public void AddTextEntry(string text, Sprite icon = null, Color color = default)
    {
        TextEntryUI entry = Instantiate(textEntryPrefab, contentArea).GetComponent<TextEntryUI>();
        entry.init(text, icon, color);
        Canvas.ForceUpdateCanvases();
        scrollRect.verticalNormalizedPosition = 0f;
    }
    public void ClearText()
    {
        foreach (Transform child in contentArea)
        {
            Destroy(child.gameObject);
        }
    }
}

