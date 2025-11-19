using Meta.XR.ImmersiveDebugger.UserInterface.Generic;
using TMPro;
using UnityEngine;

public class TextBoxUI : MonoBehaviour
{
    [SerializeField] GameObject textEntryPrefab;
    [SerializeField] RectTransform contentArea;

    public void AddTextEntry(string text)
    {
        TextEntryUI entry = Instantiate(textEntryPrefab, contentArea).GetComponent<TextEntryUI>();
        entry.init(text);
        Canvas.ForceUpdateCanvases();
    }

}
