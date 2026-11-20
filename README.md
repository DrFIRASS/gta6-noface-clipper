# GTA 6 No-Face Clipper

**Type one sentence in Claude Code. Get finished 9:16 gameplay Shorts, with the streamer's face never shown.**

`noface-clipper` is a free [Claude Code](https://claude.com/claude-code) skill. Give it a Twitch, YouTube or Kick VOD link (GTA 6 or any other game). It transcribes the stream on your computer, finds the moments where chat explodes and the voice peaks, hides the facecam, and renders vertical Shorts with word-by-word captions, a hook, a cover and ready-to-paste post text. You approve each Short, and it can post the approved ones to YouTube, TikTok and Instagram with [Blotato](https://blotato.com/?ref=firas).

Optional: put **your own HeyGen avatar** on the Shorts, commenting the action in English, as if you were the one playing.

> **Unofficial fan tool.** Not affiliated with or endorsed by Rockstar Games, Take-Two Interactive, Twitch, YouTube, Kick, TikTok, Instagram, HeyGen or Blotato. "GTA" and "Grand Theft Auto" are trademarks of Take-Two Interactive.

> ## ⚠️ Your responsibility
> noface-clipper is an editing tool. It does not give you any right to the videos you process. Streams, VODs and gameplay footage belong to their creators and to the game publisher. **You are solely responsible** for getting permission from the streamer (or joining an official clipping program) before you download, edit or publish any clip, for crediting them, and for respecting the terms of Twitch, YouTube, Kick, TikTok, Instagram and Rockstar Games / Take-Two. The authors of this skill accept no liability for how it is used.

## What you get

- **Game only.** The facecam is detected and hidden on every frame. If the stream switches to a full-screen webcam, those frames are replaced by the last game frame. Big faces with no cam overlay are blurred.
- **Built for Shorts.** The game fills a large panel over a blurred copy of itself, a hook (6 words max) sits at the top, word-by-word captions on the game, a short zoom on the peak.
- **Ready to post.** Audio normalised to -14 LUFS, a cover image, a `.txt` with title, hashtags and the streamer's credit line.
- **Quality check.** Every Short gets PASS / WARN / FAIL, including a "face visible" warning.
- **Review app.** A local web page to watch every Short and approve (A) or reject (X) it.

## Optional: your own avatar on the Shorts

If you have a [HeyGen](https://www.heygen.com) digital twin, the skill moves the game to the top of the Short and puts your talking avatar in the band under it (a large square with rounded corners). Claude writes an English commentary for each Short, sized to its length, and the captions switch to your words. The cover shows your photo and the game's name in a badge.

1. In Claude, add a custom connector with the URL `https://mcp.heygen.com/mcp/v1/` and connect your HeyGen account.
2. Ask: `add my HeyGen avatar to these Shorts`. Claude asks you to pick your avatar once, shows you the scripts and your credit balance, and generates nothing before you say yes.

It is a second pass on Shorts already made: the stream is not downloaded or transcribed again. HeyGen videos use your HeyGen plan credits. Your avatar looks real, so label these Shorts as AI content on each platform (YouTube's "altered or synthetic content", TikTok's AI label, Instagram's AI info). The skill sets the flag on YouTube and TikTok when it posts.

## Install

Requirements: [Claude Code](https://claude.com/claude-code) (paid Claude plan), Python 3.10 to 3.12, git, and ffmpeg. On a Mac, [Homebrew](https://brew.sh).

**macOS / Linux**

```bash
git clone https://github.com/DrFIRASS/gta6-noface-clipper.git ~/.claude/skills/noface-clipper
python3.12 ~/.claude/skills/noface-clipper/setup.py
```

**Windows (PowerShell)**

```powershell
winget install Gyan.FFmpeg
git clone https://github.com/DrFIRASS/gta6-noface-clipper.git "$env:USERPROFILE\.claude\skills\noface-clipper"
py -3.12 "$env:USERPROFILE\.claude\skills\noface-clipper\setup.py"
```

`setup.py` creates a private Python environment for the skill, installs its libraries and checks ffmpeg. On a Mac whose ffmpeg has no subtitle filter, it installs Homebrew's `ffmpeg-full` next to your ffmpeg and uses it for the skill only. It takes a few minutes the first time. Restart Claude Code afterwards so it sees the new skill.

**Update:** `git -C ~/.claude/skills/noface-clipper pull`, then run `setup.py` again.

## Use

Open Claude Code in an empty folder and type:

```
Make 5 Shorts from https://www.twitch.tv/videos/1234567890
```

Claude shows you the moments it picked (time range, hook, why) before rendering. The Shorts land in `clips/out/`. Then:

```
open the clipper app
```

to review them in your browser (A = approve, X = reject), and:

```
add my HeyGen avatar to these Shorts
```

for the optional avatar pass, and:

```
post my approved Shorts with Blotato on my YouTube channel, unlisted
```

to publish.

## Posting with Blotato

The skill posts through [Blotato](https://blotato.com/?ref=firas), which connects YouTube, TikTok, Instagram and more in one place.

1. Create your account on [Blotato](https://blotato.com/?ref=firas) and connect your social accounts there.
2. Connect Blotato's MCP server in Claude (Settings, then Connectors).
3. Ask Claude to post. It lists your accounts, asks you to confirm the account and the privacy, and only posts the Shorts you approved.

You can also upload the Shorts by hand for free: YouTube Studio, TikTok web upload, Meta Business Suite.

## How it finds the moments

| Signal | What it measures |
|---|---|
| Chat spikes | Twitch chat replay in 10 s buckets, 2.5x the normal rate |
| Voice peaks | 9 dB over the streamer's own normal level |
| Viewer clips and replays | Moments viewers clipped or replayed |
| Transcript | Whisper, word by word, on your computer |

A local script ranks the 30 best windows. Claude reads only those 30 lines and picks the ones with something visible happening in the game and a clear setup and payoff that a stranger understands.

## Costs

| Part | Cost |
|---|---|
| Download, transcription, detection, editing | Free, runs on your computer |
| Claude Code | Paid Claude plan |
| HeyGen (optional, for your avatar) | Your HeyGen plan credits |
| [Blotato](https://blotato.com/?ref=firas) (optional, for auto-posting) | Paid plan; you can also upload by hand for free |

## Safety

Compared to the original gta6-clipper: automatic updates are off, the review app no longer runs AI agents with permissions bypassed, autopilot scheduling is disabled, live AI modes are off, yt-dlp is never upgraded silently, links are passed safely to the downloader, and the Blotato key file is private (mode 600). Nothing is posted or generated with paid credits without your confirmation. See [CHANGELOG.md](CHANGELOG.md).

## Credits and license

Made by Dr. Firas. Based on [gta6-clipper](https://gitlab.com/nocodehack.io/gta6-clipper) by nocodehack, MIT License. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
