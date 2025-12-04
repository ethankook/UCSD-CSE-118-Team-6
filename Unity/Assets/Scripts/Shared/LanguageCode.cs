using UnityEngine;

public enum LanguageCode
{
    English,
    Spanish,
    French,
    German,
    Chinese,
    Japanese,
    Korean,
    Italian,
    Portuguese,
    Russian,
    Arabic,
}

public static class LanguageCodeExtensions
{
    public static string ToLanguageString(this LanguageCode code)
    {
        switch (code)
        {
            case LanguageCode.English:
                return "en-us";
            case LanguageCode.Spanish:
                return "es";
            case LanguageCode.French:
                return "fr";
            case LanguageCode.German:
                return "de";
            case LanguageCode.Chinese:
                return "zh";
            case LanguageCode.Japanese:
                return "ja";
            case LanguageCode.Korean:
                return "ko";
            case LanguageCode.Italian:
                return "it";
            case LanguageCode.Portuguese:
                return "pt";
            case LanguageCode.Russian:
                return "ru";
            case LanguageCode.Arabic:
                return "ar";
            default:
                return "en";
        }
    }
}
