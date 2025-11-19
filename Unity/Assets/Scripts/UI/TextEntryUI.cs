using UnityEngine;

public class TextEntryUI : MonoBehaviour
{
    [TextArea]
    public string textContent;
    [SerializeField] private TMPro.TextMeshProUGUI textBox;

    public void init(string text)
    {
        this.textContent = text;
        textBox.text = textContent;
    }
}
