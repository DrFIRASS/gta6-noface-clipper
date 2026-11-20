---
name: noface-clipper
description: Turns long gaming streams and videos (GTA 6 and any other game) into finished vertical 9:16 Shorts that show ONLY the gameplay, never the streamer's face. Takes a Twitch, YouTube or Kick VOD link or a video file, transcribes it on this computer, finds the best moments from chat spikes, voice peaks and viewer clips, hides the facecam, adds word-by-word captions, a hook, a cover and post text, runs a quality check, lets the user approve each Short, can add the user's own HeyGen avatar as a webcam under the game with an English commentary and captions, then can publish the approved ones with Blotato. Use it whenever the user wants to clip a stream, make Shorts, Reels or TikToks from a gameplay video or Twitch link, "make 5 Shorts from <link>", "clip this VOD", "gameplay only, no face", wants their avatar, face or voice commentary on the Shorts, or wants to review or post clips this skill made, even if they don't name the skill.
---
# noface-clipper

A video editor for gameplay clips. It cuts a stream into short vertical clips with captions and a credit line, shows only the game (the facecam is hidden on every frame), and never touches the game itself.

**Rights.** The user is responsible for having permission to clip and publish each streamer (direct permission or an official clipping program) and for the platforms' rules. Before the first run of a session, say this in one line, and check `SKILL/clip_rules.json` for the streamer (see step 1). Do not refuse a run over it: the decision is the user's.

`SKILL` = this folder. `PY` = `SKILL/.venv/bin/python` (Windows: `SKILL\.venv\Scripts\python.exe`). Run from the user's folder; results go to `clips/`. Steps 1 and 3 take 10+ minutes: run them in the background and check the output. Missing `SKILL/.venv`: run `python3.12 SKILL/setup.py` (see Setup in `SKILL-REFERENCE.md`).

Rare options (formats, caption styles, branding, memes, music, translation, live, voice, the app) are in `SKILL-REFERENCE.md`: read a section only when the user asks or a rule below sends you there. Never read whole transcripts: use the candidates list.

## 1. Get the source
One link (the normal case):
```
PY SKILL/watch.py <link> [START-END]
```
Downloads audio only, writes `clips/src/<id>.txt` (sentences with timestamps and tags), `<id>.json` (word timings, needed to render), `<id>.meta.json` (title, channel, link). Streams over 4 h: pass a window of about 1 h (times stay full-video times). A list of sources the user chose can go in `SKILL/channels.txt` (empty by default), then `PY SKILL/watch.py "GTA ?(6|VI)" 5`.

Tags say where to look, not what is good: `[LOUD +12dB]`, `[REPLAYED x5]`, `[CHAT x4 KEKW]` (chat spike), `[CLIPPED x2 5.6k views]` (viewers clipped it), `[MOMENT chase 0.8]`, `[HEAT 0-100]` (all signals in one number). Two tags on one line is usually the best moment.

**Clip rules:** look the streamer up in `SKILL/clip_rules.json` (`platform:handle`, lowercase). `no` = tell the user they said no to clipping and go on only if the user says they have permission; `ask` = tell the user the note; `unknown` = remind them in one line to check the channel's rules.

**Download fails:** tell the user to update yt-dlp with `PY -m pip install -U yt-dlp` and retry (do not run it silently). A bot or age check: wait 10 minutes, or ask the user before setting `CLIPPER_BROWSER=firefox` (it reads that browser's cookies).

## 2. Pick (your job)
1. `PY SKILL/nopick.py clips --candidates 30` (a few minutes on big transcripts: run it in the background). Read only `clips/candidates.txt`: the 30 best windows, one line each: `id start-end score tags | words (head ... tail)`.
2. Judge, rank, pick the best N (5 by default for a single link). To widen, shift or check a window, read only that region of `clips/src/<id>.txt` (grep the time range). Move a window's start or end to a sentence boundary; a story that needs more room gets it.
3. Before rendering run `PY SKILL/nopick.py --check clips/picks.json`: a window marked TOO SHORT ends up under 12 s. Widen it by a sentence or two, or pick another moment.
4. Fewer than N pass the rules: rerun with `--candidates 60`, then make fewer and say why. Skip ids in `clips/src/used.json` unless asked; never overlap ranges in `clips/src/moments.json`.
No AI at all: `PY SKILL/nopick.py clips [N]` writes `picks.json` directly (weaker, no premise check).

**A pick must have**
1. **Something happening in the game.** The Short shows only the gameplay, so the moment must be visible in the game: a chase, a crash, a fight, a stunt, a fail, a funny NPC, a big on-screen banner. The streamer's voice and chat are the signal and the soundtrack, not the picture. Talk about something off screen (backstory, opinions, sponsor reads, the chat, food) = 0.
2. **A premise and a payoff.** A peak (`[LOUD]`, `[CHAT]`, `[CLIPPED]`, `[REPLAYED]`, `[MOMENT chase/funny]`) and something a stranger can name said or shown before it. The payoff sits in the last 40 % and the Short ends right on it.
3. **Action first.** Second 1 shows the game in motion, not a menu, loading screen, map, pause screen or the streamer talking to the camera.
4. **No full-screen streamer.** Skip windows where the stream switches to a full-screen webcam or "just chatting" scene: those frames would be replaced by a frozen game frame.
5. **Only the game asked for** (GTA 6 unless another is named). **No spoilers or leaks:** no story endings, cutscene runs, leaked footage.
6. **Credit:** the streamer's or channel's real name (meta or words), else skip.
7. **Stands alone.** Never open on a pronoun with no antecedent, an answer without its question, or "and / but / so"; never cut mid-sentence. No two Shorts with the same point. Max 2 Shorts per source unless one link and N were asked.

**Length follows the story:** one complete beat, start one sentence before the setup, never cut the payoff to hit a number. `batch.py` rejects a window over `MAX_SPAN`.
**Text:** hook = 6 words max, caps, names the game moment (`COPS LOST HIM IN THE SWAMP`), says only what the clip shows. Title up to 70 chars; 3-5 hashtags; keywords = 1-3 words as spoken.
Write `clips/picks.json`, best first (forward slashes):
```json
[{"url": "<link from meta>", "transcript": "clips/src/<id>.json", "start": 2396.8, "end": 2421.6, "hook": "COPS LOST HIM IN THE SWAMP",
  "name": "swamp_chase", "score": 82, "title": "He lost five cop cars in the GTA 6 swamp", "hashtags": "#gta6 #gaming #shorts", "credit": "Streamer Name", "keywords": ["SWAMP", "COPS"]}]
```

**Look first:** `PY SKILL/peek.py clips/picks.json clips/peek` saves 4 frames per moment as `clips/peek/<name>.jpg`. Open them. Drop a pick if a menu, map, ad, logo card or full-screen webcam fills the picture for more than a couple of seconds, or nothing moves in the game; fix a hook that mismatches the picture; replace and re-peek. Show the user the list (score, range, hook, why) unless told to just run.

## 3. Render
```
PY SKILL/batch.py clips/picks.json clips/out
```
Layout `nocam` is the default: the facecam is found and hidden, the game fills a large panel in the middle over a blurred copy of itself, the hook sits in the band above, captions on the lower part of the game. Downloads only each moment, adds zoom, captions and hook. Per Short: `NN_<name>.mp4`, `.txt` (title, hashtags, credit), `_cover.jpg`; `clips/out/overview.jpg` = 4 frames per Short. Several minutes per Short (`CLIPPER_WORKERS=1` on a weak PC). Another layout only if the user asks for the streamer to be shown (`CLIPPER_LAYOUT=stack`).

## 4. Check
batch.py runs `qc.py` (PASS/WARN/FAIL, details `clips/out/qc.json`). FAIL: re-cut once with clip.py a sentence later or earlier as the reason says, re-run qc; still fails = drop it and say so. WARN `face visible`: open that Short's overview row and confirm it is a game character, not the streamer; if it is the streamer, drop the Short. Each `overview.jpg` row: first frame = the action (not a menu or empty street); last frame = still the moment; captions readable, hook readable, no black bars, no streamer face. Fix one alone: `PY SKILL/clip.py <url> <transcript> START END "HOOK" clips/out/<name>.mp4`, or drop it.

## 5. Hand over, approve, publish
Give each Short with its `.txt` and the QC list. Offer the review app (`PY SKILL/app.py <the user's folder>` in the background, it opens the browser; see App in the reference) so the user approves (A) or rejects (X) each Short.

Publishing happens only after the user approved the Shorts and named the account. With the Blotato MCP tools: list the accounts, confirm the target account and the privacy (`unlisted` or `private` for a test) with the user, upload each approved `.mp4`, then create the post with the title, description (title + credit line + hashtags) and the platform's required fields. Never post a Short the user did not approve. A Short with the user's avatar (step 6) is realistic AI content: YouTube `containsSyntheticMedia: true`, TikTok `isAiGenerated: true`, and tell the user to switch on Instagram's AI label in the app. Details: Post in the reference.

## 6. The user's avatar (optional, HeyGen)
Only when the user asks for their avatar, face or voice on the Shorts. A second pass on Shorts already rendered (steps 1-4): no new VOD download, transcript or pick. The game moves to the top of the Short, their talking avatar fills the free band under it (a 760 px square with rounded corners), says an English commentary you write, and the captions (on the lower part of the game) become its words; the stream sound ducks under the voice. Details and settings: Avatar in the reference.
1. **Setup once.** The HeyGen MCP tools must be connected (custom connector `https://mcp.heygen.com/mcp/v1/`; if missing, give the user that step and stop). `~/.clipper/avatar.json` holds `{"avatar_id": "<look id>"}`. Missing: list their looks (`list_avatar_looks`, ownership private, digital_twin), show them (`show_avatars`) and save the one the user picks. Never pick, invent or swap the avatar yourself.
2. `PY SKILL/avatar.py plan clips/picks.json clips/out`: per Short its length, the word budget at this voice's real speed (target, min, max), which word lands on each zoom peak, and the streamer's lines with their times and word numbers. Writes `clips/avatar/scripts.json`. Only some Shorts (the user says "only one", "just the best"): copy those picks into `clips/picks_avatar.json` and use that file in steps 2-5 instead, since batch.py renders every pick in the file it gets.
   **Voice speed.** HeyGen voices speak 2.4 to 3.8 words per second, so a guessed speed can leave the Short with a frozen face for seconds or cut the speech. `get` measures the speed on every video and saves it in avatar.json, and plan and check use it. If plan says NOT MEASURED, generate the first Short alone (step 4), then run plan again and size the other scripts with the measured speed before generating them.
3. **Write the scripts** (English, `target_words` each, inside the min-max plan prints): first person, like a streamer reacting to their own run; short spoken sentences, present tense, contractions. Sentence 1 is the hook and lands in the first 2 s. Follow the clip's order using the word numbers plan prints, and put the reaction to the payoff on the peak's word. Say only what the game shows; no facts you can't see, no brackets, emoji, hashtags or stage directions. Put 1-3 of its words in `keywords`. Fill `script` and `keywords` in `scripts.json`, then run `PY SKILL/avatar.py check clips/picks.json clips/out` and fix every script it marks TOO SHORT or TOO LONG (it says how many words to add or cut and quotes the words on each peak). Then show the user every script with their credit balance (`get_current_user`) and wait for their OK: each video spends HeyGen credits.
4. **Generate**, one Short first: `create_video_from_avatar` with `avatarId` from avatar.json, `script` verbatim, `voiceId` from avatar.json if set (else the avatar's own voice, and then no `voiceSettings`, so the speed stays the one measured), `aspectRatio: "1:1"`, `resolution: "1080p"`, `fit: "cover"`, `title: "noface-clipper <name>"`. Poll `get_video` every 30 s, then `PY SKILL/avatar.py get <video_url> clips/avatar/<name>.mp4` (it saves the video and prints the voice speed it measured). Tell the user the credits the first one used. If the measured speed differs from the one plan used by more than 10 %, run plan and check again and adjust the remaining scripts before generating them. Never resubmit a video that is still processing.
5. `PY SKILL/avatar.py attach clips/picks.json`, then `PY SKILL/batch.py clips/picks.json clips/out_avatar` (the Shorts in `clips/out` stay). `AVATAR TOO LONG` / `AVATAR SHORT` in the log, or `still_s` over 1.5 s in the Short's `.render.json` (the face holds still at the end): shorten or lengthen that script with check and regenerate that one only, after the user's OK.
   Cover: batch.py makes `<name>_cover.jpg` with `cover.py`: the user's still photo in the avatar square and the game's name in a badge at the top, in the skill's font (`cover_label` in the pick or brand.json, default `GTA 6`; never the official logo). The photo is `~/.clipper/avatar_photo.jpg`: if missing, save the chosen look's `preview_image_url` there as a JPEG once.
6. Check `clips/out_avatar/overview.jpg` (game at the top, avatar square in the bottom band, English captions on the game, game in motion) and hand over as in step 5. QC ignores the face inside the avatar cam and still watches for the streamer.

