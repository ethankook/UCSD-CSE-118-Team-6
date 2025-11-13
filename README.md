# Translation Machine

A ubiquitous computing project that integrates an AR headset (Meta Quest 2) and a voice-based smart assistant (Amazon Echo Dot) to enable **bidirectional, real-time translation** in multi-language environments such as classrooms and workplaces.

---

## Table of Contents

- [Overview](#overview)
- [Problem Space](#problem-space)
- [Intervention](#intervention)
- [Feature List](#feature-list)
- [Devices](#devices)
- [System Architecture](#system-architecture)
- [Project Timeline](#project-timeline)
- [References](#references)

---

## Overview

**Team Members**

- Ethan Kook — University of California, San Diego, USA  
- Henry Tran — University of California, San Diego, USA  
- Zilin Liu — University of California, San Diego, USA  

**Additional Keywords and Phrases**

- Human-Centered Design (HCD)  
- Ubiquitous Computing (UbiComp)  
- Automatic Speech Recognition (ASR)  
- AWS (Amazon Web Services)  
- WebSocket Secure (WSS)  
- HyperText Transfer Protocol Secure (HTTPS)  

---

## Problem Space

Language barriers create **opportunity gaps** and lead to **disproportionate experiences** in classrooms, workplaces, and everyday conversations. Individuals who are not fluent in the local language often:

- Struggle to efficiently convey their message, even when they are highly qualified.
- Are misjudged in interviews or evaluations due to language fluency, not skill or domain knowledge.
- Have difficulty following lectures or important conversations, while speakers may not realize they are not being understood.

This is an issue for both:

- **Listeners** (e.g., students who cannot fully follow the lecturer’s speech).
- **Speakers** (e.g., candidates whose skills are overlooked due to language limitations).

Existing solutions include:

- **Software:** Google Translate, Apple’s Translator  
- **Wearables:** Meta Ray-Ban smart glasses, INMO Go AR glasses  
- **Audio-based translators:** AirPods “conversation mode”, dedicated translator devices  

However, these systems are generally optimized for:

- One-to-one conversation  
- Single-language pairing  

They perform poorly in:

- Large classroom or group settings with **multiple simultaneous languages**  
- Real-time interaction where **non-verbal context** matters  
- Accessibility due to **high cost**, especially in wearable-based solutions  

👉 **Need:** A more inclusive, scalable, and human-centered translation system that supports **bidirectional communication** and **real-time interaction** in **multi-language settings**.

---

## Intervention

The proposed system integrates:

- **Meta Quest 2 AR headset**  
- **Amazon Echo Dot smart assistant**

to create a **bidirectional, real-time translation platform** that preserves natural communication flow.

### Core Experience

- The **Amazon Echo Dot** acts as a **shared audio hub**, capturing speech in the environment and forwarding it to a cloud-based ASR and translation service.
- The **AR headset** (Meta Quest 2) displays:
  - Real-time **transcription** of spoken language  
  - **Translations** in the user’s preferred language  
  - Optional **conversation context cues** (e.g., speaker identity, speaking order)

When the AR user speaks:

1. Their **audio input** is captured by the Quest microphone.
2. The speech is sent to the backend for ASR and translation.
3. The translated output is played **aloud through the Echo Dot** in the primary language of the environment (e.g., English for a classroom).

### What It Feels Like

- A student wearing the AR headset sees **live translated subtitles** during a lecture.
- When the student responds, the Echo Dot **speaks their translated response** so the professor and classmates understand.
- No one needs to:
  - Pass around phones or translation devices  
  - Pause the conversation to manually translate  

The conversation stays **continuous and human**.

### Why This Approach?

- **Scalable:** Supports multiple headset users in the same session.  
- **Low-cost:** Uses widely available consumer devices (Echo Dot, Meta Quest 2).  
- **Human-centered:** Reduces the stigma of being “the person who has to visibly translate on a phone.”

The system is designed to be demoed at the end of the quarter by showcasing a **live multi-language classroom or conversation scenario**.

---

## Feature List

| Feature                      | Description                                                     | Why It Exists                                         | Example Use Case                                                                              |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| Real-Time Transcription     | Converts spoken language into text on the AR display            | Helps users follow speech they can’t fully parse      | Student sees the professor’s lecture transcribed live in their field of view                 |
| Live Translation            | Automatically translates speech into the user’s chosen language | Reduces reliance on a shared spoken language          | Lecture is in English, but the student sees subtitles in Spanish                             |
| Reverse Translation Output  | Converts AR user speech into the speaker’s language via Echo Dot| Enables natural two-way communication                 | Student answers a question; Echo Dot speaks their response back in English                   |
| Multi-User Support *(stretch goal)* | Multiple AR users join a shared translation session            | Useful for classrooms and group conversations         | International students each receive translations in their own preferred language              |

---

## Devices

### Amazon Echo Dot

- **Role:** Primary listening and speaking unit in the environment.
- **Capabilities:**
  - Circular microphone array to capture audio from anywhere in the room.
  - Always-on listening for a wake word (e.g., “Alexa”).
  - Sends audio to **Amazon ASR services** for transcription.
- **Power:**  
  - Powered by a standard **wall outlet**.  
- **Connectivity:**  
  - Connects via **local WiFi**.

### Meta Quest 2

- **Role:** User’s visual interface for subtitles and translations.
- **Capabilities:**
  - Displays **live captions** and translated text in the user’s field of view.
  - Built-in microphone for **push-to-talk speech input**.
  - Sends user speech to the backend for **ASR → translation → TTS → Echo Dot**.
- **Power:**
  - Powered by a **rechargeable battery**.
  - Can be extended using a **USB-C power bank** if needed.

---

## System Architecture

The system uses a **client–server architecture** over a shared network with secure internet protocols.

### High-Level Components

- **Clients:**
  - Amazon Echo Dot
  - Meta Quest 2 headsets
- **Server:**
  - Central backend server handling routing, short-term storage, and language preferences.

### Networking & Protocols

- All transport uses **encrypted channels**:
  - HTTPS for REST-like communication
  - WSS (WebSocket Secure) for low-latency, bidirectional messaging

### Data Handling & Flow

#### Forward Direction (Speaker → AR Users)

1. **Echo Dot** activates on wake word and captures audio.
2. Audio is **encrypted** and sent to **AWS ASR**.
3. AWS ASR converts audio into **short text snippets** and provides **detected source language**.
4. The **backend server**:
   - Receives snippets from ASR
   - Maintains a data table of connected headsets and their **preferred target languages**
   - Groups headsets by target language
   - For each unique language group:
     - Calls translation APIs (e.g., AWS Translate)
     - Broadcasts translated text over **WSS** to all headsets in that group
   - Stores a **short-term, encrypted, anonymous transcript** for later viewing/downloading
5. **Headsets** receive translated text snippets and render subtitles in the user’s field of vision.

#### Reverse Direction (AR User → Environment / Echo Dot)

1. Headset user presses **push-to-talk**; Quest microphone captures speech.
2. Audio is streamed to the **backend server**.
3. The server:
   - Performs ASR on the audio
   - Translates the result into the **preferred language of the host/Echo Dot**
   - Uses a TTS service to synthesize audio
   - Sends the audio back to the **Echo Dot**
4. Echo Dot plays the synthesized translated audio aloud.

### Privacy & Data Retention

- **Audio:**
  - Never stored.
  - Discarded immediately after ASR or TTS processing.
- **Transcripts:**
  - Anonymous session transcript stored in the **host’s preferred language**.
  - Retained only for a **short period of time**.
  - Users can temporarily **view or download** the transcript before it is deleted.

---

## Project Timeline

Total duration: **3–4 weeks**

### Week 1

- Develop initial UI overlay for Meta Quest:
  - Subtitle placement  
  - Font size  
  - Contrast and readability
- Ensure text appears in a **non-obstructive but viewable** position.
- Set up initial **backend server** capable of communicating with Meta Quest (WebSocket or HTTP).
- Establish a basic **test environment**:
  - Quest developer mode  
  - Device pairing and connectivity  

### Week 2

- Configure **Amazon Echo Dot** for developer use.
- Implement **speech-to-text** pipeline using **AWS Transcribe** (or similar).
- Connect the backend to **receive transcribed text** from Echo Dot.
- Begin end-to-end path: real speech → live text on Quest display.

### Week 3

- Add **translation functionality** (e.g., AWS Translate / Google Translation API).
- Enable **Quest user speech capture** and route it to the server.
- Output **translated speech** through Echo Dot using TTS.
- Focus on **two-way communication stability**:
  - Latency  
  - Clarity  

### Week 4

- Refine **user experience (UX)**:
  - Readability, timing cues, color contrast.
- Optimize **latency** and **audio clarity**.
- Implement optional features if time allows:
  - Multi-user support (queue system, question filtration system)
  - Speaker identification tags
  - Adjustable subtitle speed or display options
- Conduct **full testing** with:
  - Multiple speakers  
  - Different accents  
- Prepare **final demo script** and **poster**.

---

## References

- “Documentation Home | Alexa Voice Service.” Amazon (Alexa), developer documentation.  

Content adapted from the original **CSE118 Project Proposal**. :contentReference[oaicite:0]{index=0}
