using UnityEngine;
using UnityEngine.UI;

public class TextEntryUI : MonoBehaviour
{
    [TextArea]
    public string textContent;
    [SerializeField] private TMPro.TextMeshProUGUI textBox;
    [SerializeField] private Image iconImage;
    [SerializeField] private Image messageBackground;

    public void init(string text, Sprite icon = null, Color color = default)
    {
        this.textContent = text;
        if (iconImage != null)
        {
            iconImage.sprite = icon;
        }
        if (messageBackground != null && color != default)
        {
            color = new Color(color.r, color.g, color.b, 0.7f);
            messageBackground.color = color;
        }
                if (textBox != null)
        {
            textBox.text = textContent;
        }
    }

}
