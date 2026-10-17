# Lý Lâm Lam — Avatar State API contract v1

This contract controls facial morph weights in the 3D preview only. It is **not** an AI conversation, speech, or voice API.

## Configure the endpoint

Open the preview with an explicit `avatarApi` query parameter, for example:

    https://philam-ai.github.io/Ly-lam-lam/?avatarApi=https%3A%2F%2Fapi.example.com%2Fv1%2Favatar%2Fstate

The hostname above is illustrative and does not represent a live service. No endpoint is hard-coded. Without `avatarApi`, the preview stays in local diagnostic mode and reports that the API is not configured.

The URL must use HTTPS when the preview itself is loaded over HTTPS. Credentials must not be embedded in the URL. For a protected backend, use a server-side proxy or another authenticated design rather than placing API keys in this public URL.

## Request

The browser makes a read-only HTTP `GET` request with `Accept: application/json`, no cookies, and no request body. The endpoint must allow cross-origin requests from the deployed Pages origin if it is hosted on a different origin.

The client polls every 250 ms after the previous request completes while the page is visible; polling pauses when the tab is hidden and resumes when it returns. Each request is aborted after 8 seconds if the endpoint does not respond. Failed requests use bounded exponential retry from 1.2 seconds up to 12 seconds. On a transient error, the last valid weights remain applied.

## Response schema

Return HTTP 200 with a JSON body in this shape:

    {
      "schema": "ly-lam-lam/avatar-state",
      "version": 1,
      "sequence": 12,
      "emitted_at": "2026-10-17T12:00:00Z",
      "weights": {
        "smile": 0.35,
        "mouth_open": 0.2,
        "jaw_open": 0.1
      }
    }

- `weights` may contain any subset of these morphs: `smile`, `blink_left`, `blink_right`, `mouth_open`, `jaw_open`, `jaw_hinge`, `brow_raise`, `cheek_raise`, `lip_press`, `lip_fv`, `lip_round`, `tongue_tip`.
- Each supplied weight must be a JSON number in the inclusive range 0–1. Omitted known morphs are set to 0 for that sample. Unknown morph names, invalid weights, or an unsupported schema/version are rejected.
- `sequence` and `emitted_at` are optional diagnostic fields.

## Current integration boundary

The client can consume this contract only after a real endpoint is supplied and configured. This repository does not contain the backend URL, authentication flow, conversation model, or voice service. The avatar preview does not send dialogue, audio, images, or personal data to this endpoint.
