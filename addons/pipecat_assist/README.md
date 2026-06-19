<p align="center">
  <img src="logo.png" alt="Pipecat Assist" width="320">
</p>

# Pipecat Assist

Pipecat Assist runs a realtime Pipecat voice agent inside Home Assistant. It
connects to Home Assistant MCP for device control, serves a web UI through
Ingress, and exposes a SmallWebRTC endpoint for Pipecat ESP32 satellites.

Open the web UI after starting the add-on. The first screen is the voice
assistant test surface. Pipelines are complete runtime profiles used by the UI,
Pipecat ESP32 satellites, and future Home Assistant cards.

Gemini Live is preconfigured as the default speech-to-speech profile. The UI
also includes composed realtime profiles such as `Soniox + OpenAI + Cartesia`,
`Deepgram + Gemini + Google TTS`, and `Speechmatics + AWS Nova Pro +
ElevenLabs`. Official Pipecat Flows can be enabled inside composed realtime
pipelines.

For Google Gemini Live setup and testing through Home Assistant Assist, see
`docs/gemini-live-home-assistant.md` in the repository.

Home Assistant displays this add-on with `icon.png` and `logo.png` from this
directory. The Ingress UI uses the same Pipecat mark in `/assets/logo.svg`.
