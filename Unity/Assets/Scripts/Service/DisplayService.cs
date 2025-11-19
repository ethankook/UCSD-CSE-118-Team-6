
using System.Collections;
using UnityEngine;

public class DisplayService : MonoBehaviour
{
    private string[] debugSentences = new string[]
        {
            "Hello, my name is Gemini, and I can help you with your project.",
            "The current weather outside is quite pleasant today.",
            "We are focusing on the user interface setup first.",
            "This is an example of a real-time translated sentence stream.",
            "Remember to optimize for low latency in the final AWS integration.",
            "Thank you for using this virtual reality translation application."
        };

    private float debugStreamInterval = 1.0f;
    private int sentenceIndex = 0;


    [SerializeField] private TextBoxUI textBox;

    void Start()
    {
        Debug.Log("Starting debug stream simulation...");
        // Start the fake stream simulation
        StartCoroutine(SimulateStream());
    }

    /// <summary>
    /// Coroutine to simulate receiving a translated sentence stream.
    /// </summary>
    IEnumerator SimulateStream()
    {
        while (sentenceIndex < debugSentences.Length)
        {
            yield return new WaitForSeconds(debugStreamInterval);
            textBox.AddTextEntry(debugSentences[sentenceIndex]);
            sentenceIndex++;
        }
        
        Debug.Log("Debug stream simulation finished.");
    }
}