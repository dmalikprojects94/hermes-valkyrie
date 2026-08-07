# /watch

## Purpose

Run a Claude Video-style evidence pass over a provided video source before producing conclusions. Use this for local clips, direct media files, reels/shorts recovered to local MP4, and any task where the operator expects real visual/video analysis instead of title, thumbnail, or vibes.

## Procedure

1. Identify the video source and the requested question/output. If the source is local, inspect the actual file; if a platform URL is blocked, report that as a blocker instead of fabricating analysis.
2. Produce or inspect evidence before writing conclusions:
   - `ffprobe` metadata for duration, FPS, dimensions, streams, audio.
   - sampled frames/contact sheet for visual sequence and style.
   - transcript/OCR when available or relevant.
   - audio/song/beat evidence when available; otherwise mark beat-grid/BPM as unknown.
3. Separate observed evidence from inference. Timestamp claims should cite the artifact or frame/timeline basis used.
4. For CTVE/reference-template work, output two separate artifacts:
   - **Video Analysis Card** — evidence-backed description of what happened in the reference video.
   - **Format Card** — reusable editing/template recipe derived from that analysis.
5. Save durable outputs under the target repo's private docs/artifact lane unless the operator asks for public docs. Do not commit raw downloaded videos, sampled frames, contact sheets, transcripts, or other generated media artifacts unless explicitly approved.

## Required output shape

- **Evidence Status**: full, partial_extraction, metadata_only, blocked, or needs_review.
- **Evidence Used**: file paths/commands/artifacts inspected.
- **Video Analysis Card**: source, timeline, visual observations, audio observations, edit pattern, asset inventory, evidence, confidence/unknowns.
- **Format Card**: purpose, required inputs, timeline template, shot pattern, pacing rules, music-sync rules, visual style rules, text rules, build instructions, QA checklist.
- **Gaps / Next Pass**: exact missing evidence such as beat grid, OCR, shot detection, or source re-download.

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: internal Hermes Video / Claude Video parity workflow and CTVE reference-video template-maker requirements.
- Disposition: runtime-specific-adapter for Claude Code media-video loadout.
- Notes: exposes `/watch` as an evidence-first video-analysis slash command for managed Claude Code runs.
